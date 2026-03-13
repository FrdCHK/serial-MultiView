import os
import copy
import yaml
import pandas as pd

import plugin.core.mv as mv

from core.Plugin import Plugin
from core.Context import Context
from util.integer_input import integer_input
from util.relative_position import relative_position
from util.find_matching_files import find_matching_files
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
        for key in ["max_depth", "max_ang_v", "min_z", "weight", "kalman_factor", "smo_half_window"]:
            if key in self.params:
                base_config[key] = self.params[key]

        workspace_dir = base_config.get("workspace", ".")

        for target in context.get_context().get("targets"):
            primary = target.get("primary_calibrator") or target.get("PRIMARY_CALIBRATOR")
            if primary is None:
                context.logger.error(f"Primary calibrator not found for target {target['NAME']}")
                return False
            if isinstance(primary, list):
                primary = primary[0]
            primary_ra = float(primary["RA"]) if isinstance(primary, dict) else float(primary[0]["RA"])
            primary_dec = float(primary["DEC"]) if isinstance(primary, dict) else float(primary[0]["DEC"])

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
            if_number = int(context.get_context().get("if_number", 1))
            if_column = [f"p{if_id}" for if_id in range(if_number)]
            sn_all = pd.DataFrame(columns=["t", "antenna", "calsour"] + if_column)

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
                sn_table = sn_table.loc[sn_table["p0"] != 0]
                calibrator = mv.Calibrator(int(row["ID"]), row["NAME"], row["RA"], row["DEC"], int(row["SN"]), sn_table)
                calibrator.calc_relative_position(primary_ra, primary_dec)
                secondary_calibrators.append(calibrator)
                sn_all = pd.concat([sn_all, sn_table], ignore_index=True)

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
                sn_if0 = sn_antenna[["calsour", "x", "y", "t"]].copy(deep=True)
                sn_if0["phase"] = sn_antenna["p0"]
                sn_if0.sort_values(by="t", inplace=True, ascending=True)
                sn_if0.reset_index(drop=True, inplace=True)
                antenna = mv.Antenna(int(row["ID"]), row["NAME"], sn_if0, secondary_calibrators)
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
                    mv.Gui({"ID": target["ID"], "NAME": target["NAME"]},
                           antenna, mv_config, target_relative_position, secondary_calibrators, antenna.id in conf_ids)
            else:
                antenna_ids = [a.id for a in antennas]
                while True:
                    for antenna in antennas:
                        print(f"\033[34m{antenna.id:>2d} {antenna.name}\033[0m")
                    print("\033[34m99 end\033[0m")
                    user_input = integer_input("Select an antenna (ID) to rerun")
                    if user_input in antenna_ids:
                        antenna_index = antenna_ids.index(user_input)
                        mv.Gui({"ID": target["ID"], "NAME": target["NAME"]},
                               antennas[antenna_index], mv_config, target_relative_position, secondary_calibrators, antennas[antenna_index].id in conf_ids)
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
                yaml.safe_dump(target_conf, f)

        context.logger.info("MultiView GUI run finished")
        return True
