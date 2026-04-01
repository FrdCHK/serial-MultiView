import os
import copy
import yaml
import numpy as np
import pandas as pd

from .Calibrator import Calibrator
from .Antenna import Antenna
from .Gui import Gui

from core.Plugin import Plugin
from core.Context import Context
from util.integer_input import integer_input
from util.relative_position import relative_position
from util.find_matching_files import find_matching_files
from util.yaml_util import safe_dump_builtin
from util.yes_no_input import yes_no_input


class MVRun(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Run serial MultiView GUI and save per-antenna adjustments and results. " \
               "Plugins required: MVSnExport, MVPrimaryCalibratorSelect. " \
               "Parameters optional: max_depth, max_ang_v, min_z, weight, kalman_factor, smo_half_window."

    def run(self, context: Context) -> bool:
        context.logger.info("Start MultiView GUI run")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False

        base_config = copy.deepcopy(context.get_context()["config"])
        if_freq = context.get_context().get("if_freq")
        if if_freq is None:
            if_freq = [context.get_context().get("obs_freq", 0.0) for _ in range(int(context.get_context().get("no_if", 1)))]
        base_config["if_freq"] = list(if_freq)
        for key in ["max_depth", "max_ang_v", "min_z", "weight", "kalman_factor", "smo_half_window"]:
            if key in self.params:
                base_config[key] = self.params[key]

        workspace_dir = base_config.get("workspace", ".")
        no_if = int(context.get_context().get("no_if", 1))

        for target in context.get_context().get("targets"):
            primary = target.get("primary_calibrator") or target.get("PRIMARY_CALIBRATOR")
            if primary is None:
                context.logger.error(f"Primary calibrator not found for target {target['NAME']}")
                return False
            if isinstance(primary, list):
                primary = primary[0]
            primary_ra = float(primary["RA"])
            primary_dec = float(primary["DEC"])

            target_dir = os.path.join(workspace_dir, "targets", target["NAME"])
            mv_dir = os.path.join(target_dir, "mv")
            sn_dir = os.path.join(mv_dir, "SN")
            save_dir = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}-SAVE")
            os.makedirs(save_dir, exist_ok=True)
            if not os.path.isdir(sn_dir):
                context.logger.error(f"SN directory not found: {sn_dir}")
                return False

            target_conf_path = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}.yaml")
            if os.path.isfile(target_conf_path):
                try:
                    with open(target_conf_path, "r", encoding="utf-8") as f:
                        target_conf = yaml.safe_load(f) or {}
                    if "CALIBRATORS" in target_conf:
                        target["CALIBRATORS"] = target_conf["CALIBRATORS"]
                    if "PRIMARY_CALIBRATOR" in target_conf:
                        primary = target_conf["PRIMARY_CALIBRATOR"]
                except Exception:
                    target_conf = {}
            else:
                target_conf = {}

            calibrator_table = pd.DataFrame.from_dict(target["CALIBRATORS"])
            secondary_calibrators = []
            phase_columns = [f"p{if_id}" for if_id in range(no_if)]
            delay_columns = [f"d{if_id}" for if_id in range(no_if)]
            sn_all = pd.DataFrame(columns=["t", "antenna", "calsour"] + phase_columns + delay_columns)

            for _, row in calibrator_table.iterrows():
                if int(row["ID"]) == int(primary["ID"]):
                    continue
                if "SN" not in row:
                    context.logger.error(f"SN version missing for calibrator {row['NAME']} of target {target['NAME']}")
                    return False
                sn_path = os.path.join(sn_dir, f"{target['ID']}-{target['NAME']}-SN{int(row['SN'])}.csv")
                if not os.path.isfile(sn_path):
                    context.logger.error(f"SN file not found: {sn_path}")
                    return False
                sn_table = pd.read_csv(sn_path)
                valid_phase = (sn_table[phase_columns] != 0).all(axis=1)
                sn_table = sn_table.loc[valid_phase].copy(deep=True)

                calibrator = Calibrator(int(row["ID"]), row["NAME"], row["RA"], row["DEC"], int(row["SN"]), sn_table)
                calibrator.calc_relative_position(primary_ra, primary_dec)
                secondary_calibrators.append(calibrator)
                sn_all = pd.concat([sn_all, sn_table[["t", "antenna", "calsour"] + phase_columns + delay_columns]], ignore_index=True)

            sn_all["antenna"] = sn_all["antenna"].astype(int)
            sn_all["calsour"] = sn_all["calsour"].astype(int)

            for calibrator in secondary_calibrators:
                sn_all.loc[sn_all["calsour"] == calibrator.id, ["x", "y"]] = [calibrator.dx, calibrator.dy]

            antenna_table = pd.DataFrame.from_dict(context.get_context().get("antennas", []))
            refant_id = int(context.get_context().get("ref_ant", {}).get("ID", -1))
            antennas = []
            antennas_exclude = pd.DataFrame(columns=["ID", "NAME"])
            for _, row in antenna_table.iterrows():
                if int(row["ID"]) == refant_id:
                    continue
                sn_antenna = sn_all.loc[sn_all["antenna"] == int(row["ID"])]
                if sn_antenna.shape[0] <= 10:
                    antennas_exclude.loc[antennas_exclude.index.size] = [row["ID"], row["NAME"]]
                    continue
                sn_delay = sn_antenna[["calsour", "x", "y", "t"] + phase_columns + delay_columns].copy(deep=True)
                sn_delay.sort_values(by="t", inplace=True, ascending=True)
                sn_delay.reset_index(drop=True, inplace=True)
                antenna = Antenna(int(row["ID"]), row["NAME"], sn_delay, secondary_calibrators, if_freq, no_if)
                antennas.append(antenna)

            target_relative_position = relative_position([primary_ra, primary_dec], [target["RA"], target["DEC"]])

            conf_files = []
            if os.path.isdir(save_dir):
                conf_files = find_matching_files(save_dir, f"{target['ID']}-{target['NAME']}", "CONF", "yaml")
            mv_flag = bool(conf_files)
            conf_ids = {conf_id for _, conf_id, _ in conf_files}
            run_all_flag = True
            if mv_flag and ("run_all" not in self.params):
                run_all_flag = yes_no_input(f"{target['NAME']} already has saved MV configs. Rerun all antennas?", default=False)
            elif "run_all" in self.params:
                run_all_flag = bool(self.params["run_all"])

            mv_config = copy.deepcopy(base_config)
            mv_config["mv_workspace"] = os.path.join(workspace_dir, "targets", target["NAME"], "mv")

            if run_all_flag:
                for antenna in antennas:
                    Gui({"ID": target["ID"], "NAME": target["NAME"], "RA": target["RA"], "DEC": target["DEC"]},
                        primary, antenna, mv_config, target_relative_position, secondary_calibrators, antenna.id in conf_ids)
            else:
                antenna_ids = [a.id for a in antennas]
                while True:
                    for antenna in antennas:
                        print(f"\033[34m{antenna.id:>2d} {antenna.name}\033[0m")
                    print("\033[34m99 end\033[0m")
                    user_input = integer_input("Select an antenna (ID) to rerun")
                    if user_input in antenna_ids:
                        antenna_index = antenna_ids.index(user_input)
                        Gui({"ID": target["ID"], "NAME": target["NAME"], "RA": target["RA"], "DEC": target["DEC"]},
                            primary, antennas[antenna_index], mv_config, target_relative_position, secondary_calibrators,
                            antennas[antenna_index].id in conf_ids)
                    elif user_input == 99:
                        break
                    else:
                        print("\033[31mInvalid input!\033[0m")

            target_conf["MV_FLAG"] = True
            target_conf["ANTENNAS_EXCLUDE"] = antennas_exclude.to_dict()
            target_conf["PRIMARY_CALIBRATOR"] = primary
            target_conf["CALIBRATORS"] = target["CALIBRATORS"]
            os.makedirs(mv_dir, exist_ok=True)
            with open(target_conf_path, "w", encoding="utf-8") as f:
                safe_dump_builtin(target_conf, f)

        context.logger.info("MultiView GUI run finished")
        return True
