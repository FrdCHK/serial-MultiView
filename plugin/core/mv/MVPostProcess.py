"""
MultiView post-process: SN import, SPLIT, UVFLG, IMAGR, JMFIT, FITTP.
@Author: Jingdong Zhang
@DATE  : 2026/03/12
"""
import os
import math
import yaml
import numpy as np
import pandas as pd
import scipy.interpolate as interp
from typing import Dict, Any
from Wizardry.AIPSData import AIPSUVData as WizAIPSData

from core.Plugin import Plugin
from core.Context import Context
from util.find_matching_files import find_matching_files
from util.float_to_time_components import float_to_time_components
from util.map_center import map_center
from util.summary import summary


class MVPostProcess(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Apply MultiView SN tables, run CLCAL, SPLIT, IMAGR, and optional JMFIT. " \
               "Plugins required: AipsCatalog, GeneralTask, Imagr, PRCalibratorFringeFitting, MVRun. " \
               "Parameters required: indisk, cellsize, imsize, niter, gain, ltype, uvwtfn; optional: jmfit, aparm."

    def run(self, context: Context) -> bool:
        context.logger.info("Start MultiView post-process")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False

        workspace_dir = context.get_context()["config"]["workspace"]
        indisk = int(self.params["indisk"])
        jmfit_flag = bool(self.params.get("jmfit", True))

        for target in context.get_context().get("targets"):
            context.logger.info(f"MV post-process target {target['ID']} {target['NAME']}")
            primary = target.get("primary_calibrator") or target.get("PRIMARY_CALIBRATOR")
            if primary is None:
                context.logger.error(f"Primary calibrator not found for target {target['NAME']}")
                return False
            if isinstance(primary, list):
                primary = primary[0]
            context.logger.info(f"Primary calibrator: {primary['ID']} {primary['NAME']}")

            target_dir = os.path.join(workspace_dir, "targets", target["NAME"])
            mv_dir = os.path.join(target_dir, "mv")
            target_conf_path = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}.yaml")
            target_conf: Dict[str, Any] = {}
            if os.path.isfile(target_conf_path):
                try:
                    with open(target_conf_path, "r", encoding="utf-8") as f:
                        target_conf = yaml.safe_load(f) or {}
                except Exception:
                    target_conf = {}
            # if "RASHIFT" in target_conf:
            #     target["RASHIFT"] = target_conf["RASHIFT"]
            # if "DECSHIFT" in target_conf:
            #     target["DECSHIFT"] = target_conf["DECSHIFT"]

            antennas_exclude = pd.DataFrame.from_dict(target_conf.get("ANTENNAS_EXCLUDE", {}))
            if not antennas_exclude.empty:
                context.logger.debug(f"Excluded antennas for {target['NAME']}: {antennas_exclude['NAME'].tolist()}")

            params_target = {"in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
            if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target):
                context.logger.error(f"Target SPLAT catalog not found for {target['NAME']}")
                return False
            context.logger.debug(f"SPLAT catalog seq for {target['NAME']}: {params_target['inseq']}")

            splat = WizAIPSData(target["NAME"], "SPLAT", indisk, int(params_target["inseq"]))
            primary_sn_sources = [f"FRING({primary['NAME']} STRUC)", f"FRING({primary['NAME']})"]
            ext = {"status": False}
            primary_sn_src = ""
            for source in primary_sn_sources:
                ext = context.get_context()["loaded_plugins"]["AipsCatalog"].search_ext(
                    context,
                    target["NAME"],
                    "SPLAT",
                    indisk,
                    int(params_target["inseq"]),
                    "SN",
                    ext_source=source,
                )
                if ext["status"]:
                    primary_sn_src = source
                    break
            if not ext["status"]:
                context.logger.error(f"Primary SN table not found for target {target['NAME']}")
                return False
            primary_snver = context.get_context()["aips_catalog"][ext["cat_index"]]["ext"][ext["ext_index"]]["version"][ext["ver_index"]]["num"]
            context.logger.debug(f"Primary SN version for {target['NAME']}: {primary_snver}")
            sn0 = splat.table("SN", int(primary_snver))

            mv_snver = context.get_context()["loaded_plugins"]["AipsCatalog"].get_highest_ext_ver(
                context, target["NAME"], "SPLAT", indisk, int(params_target["inseq"]), "SN"
            ) + 1
            context.logger.debug(f"New MV SN version for {target['NAME']}: {mv_snver}")
            sn_mv = splat.attach_table("SN", int(mv_snver))

            mv_data_dir = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}-MV")
            mv_cache = {}
            mv_delay_cache = {}
            save_dir = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}-SAVE")
            if os.path.isdir(save_dir):
                conf = find_matching_files(save_dir, f"{target['ID']}-{target['NAME']}", "CONF", "yaml")
            else:
                conf = []
            context.logger.debug(f"MV config files found for {target['NAME']}: {len(conf)}")
            skipped_refant = 0
            skipped_excluded = 0
            skipped_missing_conf = 0
            skipped_missing_mv = 0
            appended_rows = 0
            for row in sn0:
                an_id = int(row.antenna_no)
                if an_id == int(context.get_context().get("ref_ant", {}).get("ID", -1)):
                    skipped_refant += 1
                    sn_mv.append(row)
                    continue
                if not antennas_exclude.empty:
                    if not antennas_exclude.loc[antennas_exclude["ID"] == an_id].empty:
                        skipped_excluded += 1
                        sn_mv.append(row)
                        continue
                if an_id not in mv_cache:
                    an_name = None
                    for _, conf_id, conf_name in conf:
                        if conf_id == an_id:
                            an_name = conf_name
                            break
                    if an_name is None:
                        skipped_missing_conf += 1
                        sn_mv.append(row)
                        continue
                    mv_path = os.path.join(mv_data_dir, f"{target['ID']}-{target['NAME']}-{an_id}-{an_name}.csv")
                    if not os.path.isfile(mv_path):
                        skipped_missing_mv += 1
                        sn_mv.append(row)
                        continue
                    mv_cache[an_id] = pd.read_csv(mv_path)
                    mv_delay_path = os.path.join(mv_data_dir, f"{target['ID']}-{target['NAME']}-{an_id}-{an_name}-DELAY.csv")
                    if os.path.isfile(mv_delay_path):
                        mv_delay_cache[an_id] = pd.read_csv(mv_delay_path)
                sn_f = mv_cache[an_id]
                delay_f = mv_delay_cache.get(an_id)
                if_freq = context.get_context().get("if_freq", None)
                if if_freq is None:
                    if_freq = np.array([context.get_context().get("obs_freq", 0.0) for _ in range(int(context.get_context().get("no_if", 1)))])
                else:
                    if_freq = np.array(if_freq)
                for j in range(int(context.get_context().get("no_if", 1))):
                    phase0 = math.atan2(row.imag1[j], row.real1[j])
                    phase0_corr = phase0
                    if delay_f is not None and not delay_f.empty:
                        delay_col = f"d{j}"
                        if delay_col in delay_f.columns:
                            fd = interp.interp1d(delay_f["t"], delay_f[delay_col], bounds_error=False, fill_value="extrapolate")
                            delay_corr = float(fd(row.time))
                        elif "mbdelay" in delay_f.columns:
                            fd = interp.interp1d(delay_f["t"], delay_f["mbdelay"], bounds_error=False, fill_value="extrapolate")
                            delay_corr = float(fd(row.time))
                        else:
                            delay_corr = 0.0

                        try:
                            corrected_delay = row.delay_1[j] + delay_corr
                            row.delay_1[j] = corrected_delay
                        except Exception:
                            corrected_delay = delay_corr
                        phase_offset = delay_corr * if_freq[j] * 2e9 * math.pi
                        phase0_corr = phase0 + phase_offset
                        # phase0_corr = (phase0_corr + np.pi) % (2 * np.pi) - np.pi
                    f = interp.interp1d(sn_f["t"], sn_f["phase"], bounds_error=False, fill_value="extrapolate")
                    phase = f(row.time) + phase0_corr
                    # phase = (phase + np.pi) % (2 * np.pi) - np.pi
                    row.real1[j] = math.cos(phase)
                    row.imag1[j] = math.sin(phase)
                    row.real2[j] = math.cos(phase)
                    row.imag2[j] = math.sin(phase)
                appended_rows += 1
                sn_mv.append(row)
            context.logger.debug(
                f"SN rows appended: {appended_rows}; skipped ref_ant={skipped_refant}, "
                f"excluded={skipped_excluded}, missing_conf={skipped_missing_conf}, missing_mv={skipped_missing_mv}"
            )

            sn0.close()
            sn_mv.close()
            context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(
                context,
                target["NAME"],
                "SPLAT",
                indisk,
                int(params_target["inseq"]),
                "SN",
                ext_version=int(mv_snver),
                ext_source="MV",
            )
            context.logger.info(f"MultiView SN{mv_snver} for {target['NAME']} imported to AIPS")

            # CLCAL with MV SN
            context.logger.info(f"CLCAL(MV) for {target['NAME']}")
            task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({
                "inname": target["NAME"],
                "inclass": "SPLAT",
                "indisk": indisk,
                "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                "calsour": [primary["NAME"]],
                # "sources": [target["NAME"]],
                "opcode": "CALI",
                "interpol": "AMBG",
                "smotyp": "VLBI",
                "samptype": "BOX",
                "bparm": [0, 0, 1, 0],
                "sn_source": "MV",
                "cl_source": "SPLAT",
                "identifier": "CLCAL(MV)",
            })
            task_clcal.run(context)

            primary_cl_sources = [f"CLCAL(FRING({primary['NAME']} STRUC))", f"CLCAL(FRING({primary['NAME']}))"]
            primary_cl_source = primary_cl_sources[-1]
            for source in primary_cl_sources:
                ext = context.get_context()["loaded_plugins"]["AipsCatalog"].search_ext(
                    context,
                    target["NAME"],
                    "SPLAT",
                    indisk,
                    int(params_target["inseq"]),
                    "CL",
                    ext_source=source,
                )
                if ext["status"]:
                    primary_cl_source = source
                    break

            context.logger.info(f"SPLIT(PR) for {target['NAME']}")
            self.split_only(context, target, indisk, "PR", primary_cl_source)
            context.logger.info(f"SPLIT(MV) for {target['NAME']}")
            self.split_only(context, target, indisk, "MV", "CLCAL(MV)")

            save_dir = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}-SAVE")
            if os.path.isdir(save_dir):
                conf_files = find_matching_files(save_dir, f"{target['ID']}-{target['NAME']}", "CONF", "yaml")
                context.logger.debug(f"UVFLG configs for {target['NAME']}: {len(conf_files)}")
                self.apply_uvflg(context, target, indisk, conf_files)
            if not antennas_exclude.empty:
                context.logger.debug(f"UVFLG exclude antennas for {target['NAME']}: {antennas_exclude['ID'].tolist()}")
                for _, row in antennas_exclude.iterrows():
                    self.run_uvflg(context, target, indisk, int(row["ID"]), [0 for _ in range(8)], "PR")
                    self.run_uvflg(context, target, indisk, int(row["ID"]), [0 for _ in range(8)], "MV")

            pr_split_ident = f"{target['NAME']} PR"
            if ("rashift" not in target) or ("decshift" not in target):
                context.logger.info(f"Determining map center using {pr_split_ident}")
                if not map_center(context, target, pr_split_ident, indisk):
                    return False
            context.logger.info(f"Map center for {target['NAME']}: rashift={target['rashift']}, decshift={target['decshift']}")

            context.logger.info(f"IMAGR(PR) for {target['NAME']}")
            self.run_imagr(context, target, indisk, "PR")
            context.logger.info(f"IMAGR(MV) for {target['NAME']}")
            self.run_imagr(context, target, indisk, "MV")

            if jmfit_flag:
                context.logger.info(f"JMFIT(PR) for {target['NAME']}")
                self.run_jmfit(context, target, indisk, "PR")
                context.logger.info(f"JMFIT(MV) for {target['NAME']}")
                self.run_jmfit(context, target, indisk, "MV")
                try:
                    summary(os.path.join(workspace_dir, "targets", target["NAME"]), target, True, True)
                    context.logger.info(f"Summary written for {target['NAME']}")
                except FileNotFoundError as e:
                    context.logger.warning(f"Summary skipped due to missing JMFIT file: {e}")

            context.logger.info(f"FITTP(PR) for {target['NAME']}")
            self.export_fits(context, target, indisk, "PR")
            context.logger.info(f"FITTP(MV) for {target['NAME']}")
            self.export_fits(context, target, indisk, "MV")

        context.logger.info("MultiView post-process finished")
        return True

    def split_only(self, context: Context, target: Dict[str, Any], indisk: int, tag: str, cl_source: str) -> None:
        params_target = {"in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
        context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target)
        cl_params = {
            "inname": target["NAME"],
            "inclass": "SPLAT",
            "indisk": indisk,
            "inseq": int(params_target["inseq"]),
            "cl_source": cl_source,
        }
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, cl_params, "CL", "gainuse"):
            context.logger.error(f"CL source not found: {cl_source}")
            return
        context.logger.debug(f"SPLIT({tag}) gainuse={cl_params['gainuse']} cl_source={cl_source}")
        params_split = {
            "inname": target["NAME"],
            "inclass": "SPLAT",
            "indisk": indisk,
            "inseq": int(params_target["inseq"]),
            "sources": [target["NAME"]],
            "docalib": 1,
            "gainuse": cl_params["gainuse"],
            "outdisk": indisk,
            "aparm": self.params.get("aparm", [2, 0]),
        }

        task_split = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "SPLIT", **params_split})
        task_split.run(context)

        split_ident = f"{target['NAME']} {tag}"
        try:
            context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(
                context, target["NAME"], "SPLIT", indisk, split_ident, history="Created by SPLIT"
            )
        except Exception:
            pass

    def apply_uvflg(self, context: Context, target: Dict[str, Any], indisk: int, conf_files) -> None:
        save_dir = os.path.join(context.get_context()["config"]["workspace"], "targets", target["NAME"], "mv", f"{target['ID']}-{target['NAME']}-SAVE")
        for filename, antenna_id, _ in conf_files:
            conf_dir = os.path.join(save_dir, filename)
            with open(conf_dir, "r", encoding="utf-8") as f:
                an_conf = yaml.safe_load(f) or {}
            if "t_flag" not in an_conf:
                continue
            for timerange in an_conf["t_flag"]:
                timerang = [0 for _ in range(8)]
                timerang[:4] = float_to_time_components(timerange[0])
                timerang[4:] = float_to_time_components(timerange[1])
                context.logger.debug(f"UVFLG antenna={antenna_id} timerang={timerang}")
                self.run_uvflg(context, target, indisk, antenna_id, timerang, "PR")
                self.run_uvflg(context, target, indisk, antenna_id, timerang, "MV")

    def run_uvflg(self, context: Context, target: Dict[str, Any], indisk: int, antenna_id: int, timerang, tag: str) -> None:
        params_split = {"in_cat_ident": f"{target['NAME']} {tag}"}
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_split):
            context.logger.error(f"SPLIT catalog not found for UVFLG: {target['NAME']} {tag}")
            return
        task_uvflg = context.get_context()["loaded_plugins"]["GeneralTask"]({
            "task_name": "UVFLG",
            "inname": target["NAME"],
            "inclass": "SPLIT",
            "indisk": indisk,
            "inseq": params_split["inseq"],
            "antennas": [int(antenna_id)],
            "timerang": timerang,
        })
        task_uvflg.run(context)

    def export_fits(self, context: Context, target: Dict[str, Any], indisk: int, tag: str) -> None:
        split_ident = f"{target['NAME']} {tag}"
        imagr_ident = f"{split_ident} IMAGR"
        base_dir = os.path.join(context.get_context()["config"]["workspace"], "targets", target["NAME"])
        params_split = {"in_cat_ident": split_ident}
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_split):
            context.logger.error(f"SPLIT catalog not found for FITTP: {split_ident}")
            return
        split_path = os.path.join(base_dir, f"{target['ID']}-{target['NAME']}-SPLIT-{tag}.fits")
        task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({
            "task_name": "FITTP",
            "inname": target["NAME"],
            "inclass": "SPLIT",
            "indisk": indisk,
            "inseq": params_split["inseq"],
            "dataout": split_path,
        })
        task_fittp.run(context)

        params_imagr = {"in_cat_ident": imagr_ident}
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_imagr):
            context.logger.error(f"IMAGR catalog not found for FITTP: {imagr_ident}")
            return
        img_path = os.path.join(base_dir, f"{target['ID']}-{target['NAME']}-{tag}.fits")
        task_fittp_img = context.get_context()["loaded_plugins"]["GeneralTask"]({
            "task_name": "FITTP",
            "inname": target["NAME"],
            "inclass": "ICL001",
            "indisk": indisk,
            "inseq": params_imagr["inseq"],
            "dataout": img_path,
        })
        task_fittp_img.run(context)

    def run_jmfit(self, context: Context, target: Dict[str, Any], indisk: int, tag: str) -> None:
        imagr_ident = f"{target['NAME']} {tag} IMAGR"
        params_imagr = {"in_cat_ident": imagr_ident}
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_imagr):
            context.logger.error(f"IMAGR catalog not found for JMFIT: {imagr_ident}")
            return
        jmfit_path = os.path.join(context.get_context()["config"]["workspace"], "targets", target["NAME"], f"{target['ID']}-{target['NAME']}-{tag}.jmfit")
        task_jmfit = context.get_context()["loaded_plugins"]["GeneralTask"]({
            "task_name": "JMFIT",
            "inname": target["NAME"],
            "inclass": "ICL001",
            "indisk": indisk,
            "inseq": params_imagr["inseq"],
            "doprint": -3,
            "prtlev": 2,
            "fitout": jmfit_path,
            "niter": self.params["niter"],
        })
        task_jmfit.run(context)

    def run_imagr(self, context: Context, target: Dict[str, Any], indisk: int, tag: str) -> None:
        split_ident = f"{target['NAME']} {tag}"
        imagr_ident = f"{split_ident} IMAGR"
        rashift = float(target["rashift"])
        decshift = float(target["decshift"])
        cellsize = self.params["cellsize"]
        imsize = self.params["imsize"]
        if not isinstance(cellsize, list):
            cellsize = [cellsize, cellsize]
        if not isinstance(imsize, list):
            imsize = [imsize, imsize]
        context.logger.debug(f"IMAGR({tag}) params: cellsize={cellsize}, imsize={imsize}, "
                            f"niter={self.params['niter']}, gain={self.params['gain']}, "
                            f"ltype={self.params['ltype']}, uvwtfn={self.params['uvwtfn']}, "
                            f"rashift={rashift}, decshift={decshift}")
        task_imagr = context.get_context()["loaded_plugins"]["Imagr"]({
            "inname": target["NAME"],
            "inclass": "SPLIT",
            "indisk": indisk,
            "in_cat_ident": split_ident,
            "srcname": target["NAME"],
            "cellsize": cellsize,
            "imsize": imsize,
            "niter": self.params["niter"],
            "gain": self.params["gain"],
            "nfield": 1,
            "ltype": self.params["ltype"],
            "rashift": [rashift],
            "decshift": [decshift],
            "uvwtfn": self.params["uvwtfn"],
            "dotv": 0,
            "out_cat_ident": imagr_ident,
        })
        task_imagr.run(context)
