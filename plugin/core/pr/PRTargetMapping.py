import os
import re
import pandas as pd
from typing import Dict, Any
from AIPSData import AIPSImage

from core.Plugin import Plugin
from core.Context import Context
from util.yes_no_input import yes_no_input
from util.integer_input import integer_input
from util.float_input import float_input


class PRTargetMapping(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fitting for all calibrators. Plugin PRCalibratorFringeFitting must be run before. If structure correction is used, PRCalibratorMapping & PRCalibratorStructureCorrection also must be run before." \
               "Plugins required: AipsCatalog, FitsExport, Imagr, GeneralTask, PRCalibratorFringeFitting. " \
               "Parameter required: indisk, structure, imagr, cellsize, imsize, niter, gain, ltype, uvwtfn, jmfit, niter; optional: aparm for AIPS task SPLIT."

    def run(self, context: Context) -> bool:
        context.logger.info("Start PR target mapping")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        for target in context.get_context().get("targets"):
            params_target = {"in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target)
            target_dir = os.path.join(targets_dir, target["NAME"])
            jmfit_list = []
            for calibrator in target["CALIBRATORS"]:
                if self.params["structure"]:
                    cl_source = f"CALIB({calibrator['NAME']})"
                    ident_struc_suffix = f" {calibrator['NAME']} ST"
                else:
                    cl_source = f"CLCAL(FRING({calibrator['NAME']}))"
                    ident_struc_suffix = f" {calibrator['NAME']}"
                out_cat_ident_suffix = f" PR{ident_struc_suffix}"
                params_split = {"inname": target["NAME"],
                                "inclass": "SPLAT",
                                "indisk": self.params["indisk"],
                                "inseq": params_target["inseq"],
                                "cl_source": cl_source}
                context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, params_split, "CL", "gainuse")
                if not context.get_context()["loaded_plugins"]["FitsExport"].export(context,
                                                                                    target["NAME"],
                                                                                    "SPLAT",
                                                                                    self.params["indisk"],
                                                                                    params_target["inseq"],
                                                                                    params_split["gainuse"],
                                                                                    target["NAME"],
                                                                                    target_dir,
                                                                                    self.params["aparm"] if "aparm" in self.params else [2, 0],
                                                                                    out_cat_ident_suffix,
                                                                                    f"{out_cat_ident_suffix} UV"):
                    context.logger.error(f"Error in target FITS export")
                    return False
                
                if self.params["imagr"]:
                    # determine map center
                    split_cat_ident = f"{target['NAME']}{out_cat_ident_suffix}"
                    if not self.map_center(context, target, split_cat_ident):
                        return False
                    
                    task_imagr = context.get_context()["loaded_plugins"]["Imagr"]({"inname": target["NAME"],
                                                                                   "inclass": "SPLIT",
                                                                                   "indisk": self.params["indisk"],
                                                                                   "in_cat_ident": split_cat_ident,
                                                                                   "srcname": target["NAME"],
                                                                                   "cellsize": self.params["cellsize"],
                                                                                   "imsize": self.params["imsize"],
                                                                                   "niter": self.params["niter"],
                                                                                   "gain": self.params["gain"],
                                                                                   "nfield": 1,
                                                                                   "ltype": self.params["ltype"],
                                                                                   "rashift": [target["rashift"]],
                                                                                   "decshift": [target["decshift"]],
                                                                                   "uvwtfn": self.params["uvwtfn"],
                                                                                   "dotv": 1,
                                                                                   "out_cat_ident": split_cat_ident})
                    task_imagr.run(context)

                    if self.params["jmfit"]:
                        jmfit_file = os.path.join(target_dir, f"{target['NAME']}{out_cat_ident_suffix}.jm")
                        if not self.jmfit(context, target, split_cat_ident, jmfit_file):
                            return False
                        jmfit_sum = self.jmfit_summary(context, jmfit_file)
                        if jmfit_sum:
                            print(f"JMFIT quality\n  PEAK: {jmfit_sum['PEAK']:>6.2e}\n  RMS: {jmfit_sum['RMS']:>6.2e}\n  SNR: {jmfit_sum['SNR']:>6.2f}")
                        if (self.params["uvwtfn"] != "NA") and ((jmfit_sum == {}) or (jmfit_sum["SNR"] < 15)):
                            if yes_no_input("JMFIT failed or low SNR. Do you wish to try natual weighting for a higher SNR?", default=True):
                                na_cat_ident = f"{split_cat_ident} NA"
                                task_imagr = context.get_context()["loaded_plugins"]["Imagr"]({"inname": target["NAME"],
                                                                                               "inclass": "SPLIT",
                                                                                               "indisk": self.params["indisk"],
                                                                                               "in_cat_ident": split_cat_ident,
                                                                                               "srcname": target["NAME"],
                                                                                               "cellsize": self.params["cellsize"],
                                                                                               "imsize": self.params["imsize"],
                                                                                               "niter": self.params["niter"],
                                                                                               "gain": self.params["gain"],
                                                                                               "nfield": 1,
                                                                                               "ltype": self.params["ltype"],
                                                                                               "rashift": [target["rashift"]],
                                                                                               "decshift": [target["decshift"]],
                                                                                               "uvwtfn": "NA",
                                                                                               "dotv": 1,
                                                                                               "out_cat_ident": na_cat_ident})
                                task_imagr.run(context)
                                jmfit_na_file = os.path.join(target_dir, f"{target['NAME']}{out_cat_ident_suffix} NA.jm")
                                if not self.jmfit(context, target, na_cat_ident, jmfit_na_file):
                                    return False
                                jmfit_na_sum = self.jmfit_summary(context, jmfit_na_file)
                                if jmfit_na_sum:
                                    print(f"JMFIT quality (NA weighting)\n  PEAK: {jmfit_na_sum['PEAK']:.3e}\n  RMS: {jmfit_na_sum['RMS']:.3e}\n  SNR: {jmfit_na_sum['SNR']:.2f}")
                                jmfit_na_sum["CALIBRATOR"] = calibrator["NAME"]
                                jmfit_na_sum["WEIGHT"] = "NA"
                                jmfit_list.append(jmfit_na_sum)
                                # export ICL001 (NA)
                                params_icl = {"in_cat_ident": na_cat_ident}
                                context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_icl)
                                fits_dir = os.path.join(target_dir, f"{target['NAME']}{out_cat_ident_suffix} NA.fits")
                                task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "FITTP",
                                                                                                     "inname": target["NAME"],
                                                                                                     "inclass": "ICL001",
                                                                                                     "indisk": self.params["indisk"],
                                                                                                     "inseq": params_icl["inseq"],
                                                                                                     "dataout": fits_dir})
                                task_fittp.run(context)
                        jmfit_sum["CALIBRATOR"] = calibrator["NAME"]
                        jmfit_sum["WEIGHT"] = "UN"  # uniform weighting, by default
                        jmfit_list.append(jmfit_sum)
                    # export ICL001
                    params_icl = {"in_cat_ident": split_cat_ident}
                    context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_icl)
                    fits_dir = os.path.join(target_dir, f"{target['NAME']}{out_cat_ident_suffix}.fits")
                    task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "FITTP",
                                                                                         "inname": target["NAME"],
                                                                                         "inclass": "ICL001",
                                                                                         "indisk": self.params["indisk"],
                                                                                         "inseq": params_icl["inseq"],
                                                                                         "dataout": fits_dir})
                    task_fittp.run(context)
                    context.logger.info(f"Target {target['NAME']} mapping with calibrator {calibrator['NAME']} finished")
            # export JMFIT summary for this target
            if self.params["jmfit"]:
                jmfit_sum_df = pd.DataFrame(jmfit_list)
                sum_csv = os.path.join(target_dir, f"{target['NAME']}{' ST' if self.params['structure'] else ''} JMFIT SUMMARY.csv")
                jmfit_sum_df.to_csv(sum_csv, index=False)
                context.logger.info(f"JMFIT summary of target {target['NAME']} saved to {sum_csv}")
            context.logger.info(f"Target {target['NAME']} mapping finished")

        context.logger.info("PR target mapping finished")
        return True
    
    def map_center(self, context: Context, target: Dict[str, Any], split_cat_ident: str) -> bool:
        cellsize = 5e-4
        imsize = 512
        rashift = 0
        decshift = 0

        try:
            # IMAGR loop until user is satisfied with the parameters
            while True:
                if yes_no_input("Do you wish to run IMAGR with AIPSTV to determine RA and DEC offsets?", default=True):
                    print(f"\033[34mRunning IMAGR with cellsize={cellsize:<8f}, imsize={imsize:<4d}, rashift={rashift:<8f}, and decshift={decshift:<8f}\033[0m")
                    task_imagr = context.get_context()["loaded_plugins"]["Imagr"]({"inname": target["NAME"],
                                                                                   "inclass": "SPLIT",
                                                                                   "indisk": self.params["indisk"],
                                                                                   "in_cat_ident": split_cat_ident,
                                                                                   "srcname": target["NAME"],
                                                                                   "cellsize": [cellsize, cellsize],
                                                                                   "imsize": [imsize, imsize],
                                                                                   "nfield": 1,
                                                                                   "niter": 500,
                                                                                   "ltype": -4,
                                                                                   "rashift": [rashift],
                                                                                   "decshift": [decshift],
                                                                                   "dotv": 1,
                                                                                   "out_cat_ident": "TEMP"})
                    task_imagr.run(context)
                else:
                    rashift = float_input(f"{target['NAME']} rashift (arcsec)", rashift)
                    decshift = float_input(f"{target['NAME']} decshift (arcsec)", decshift)
                    target["rashift"] = rashift
                    target["decshift"] = decshift
                    break

                params_target = {"in_cat_ident": "TEMP"}
                context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target)
                ibm = AIPSImage(target['NAME'], "IBM001", self.params["indisk"], params_target['inseq'])
                icl = AIPSImage(target['NAME'], "ICL001", self.params["indisk"], params_target['inseq'])
                if yes_no_input("Do you wish to adjust IMAGR parameters?", default=True):
                    cellsize = float_input("cellsize", cellsize)
                    imsize = integer_input("imsize", imsize)
                    rashift = float_input("rashift (arcsec)", rashift)
                    decshift = float_input("decshift (arcsec)", decshift)
                    if ibm.exists():
                        ibm.zap()
                        context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "IBM001", self.params["indisk"], params_target['inseq'])
                    if icl.exists():
                        icl.zap()
                        context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "ICL001", self.params["indisk"], params_target['inseq'])
                    continue
                else:
                    if yes_no_input("Do you wish to determine offsets automatically from clean component? Make sure you have cleaned during IMAGR.", default=True):
                        icl = AIPSImage(target['NAME'], "ICL001", self.params["indisk"], params_target['inseq'])
                        cc_table = icl.table("AIPS CC", 0)
                        # NOTE: unit in CC table is degree
                        rashift = cc_table[0]["deltax"] * 3600
                        decshift = cc_table[0]["deltay"] * 3600
                        target["rashift"] = rashift
                        target["decshift"] = decshift
                    else:
                        rashift = float_input("rashift (arcsec)", rashift)
                        decshift = float_input("decshift (arcsec)", decshift)
                        target["rashift"] = rashift
                        target["decshift"] = decshift
                    if ibm.exists():
                        ibm.zap()
                        context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "IBM001", self.params["indisk"], params_target['inseq'])
                    if icl.exists():
                        icl.zap()
                        context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "ICL001", self.params["indisk"], params_target['inseq'])
                    break
        except Exception as e:
            context.logger.error(f"Error in map center determination: {e}")
            return False
        else:
            context.logger.debug(f"Map center determined: {rashift:<8f}, {decshift:<8f}")
            return True
    
    def jmfit(self, context: Context, target: Dict[str, Any], icl_cat_ident: str, fitout: str) -> bool:
        params_icl = {"in_cat_ident": icl_cat_ident}
        context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_icl)
        task_jmfit = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "JMFIT",
                                                                             "inname": target['NAME'],
                                                                             "inclass": "ICL001",
                                                                             "indisk": self.params["indisk"],
                                                                             "inseq": params_icl["inseq"],
                                                                             "doprint": -3,
                                                                             "prtlev": 2,
                                                                             "fitout": fitout,
                                                                             "niter": self.params["niter"]})
        if not task_jmfit.run(context):
            context.logger.info(f"JMFIT failed")
            return False
        return True

    def jmfit_summary(self, context, jmfit_file: str) -> Dict[str, Any]:
        summary = {}
        try:
            with open(jmfit_file, 'r', encoding='utf-8') as file:
                for line in file:
                    pattern = re.compile(r'Solution RMS\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*in\d+\s*usable pixels')
                    match = pattern.search(line)
                    if match:
                        summary['RMS'] = float(match.group(1))
                        continue
                    pattern = re.compile(r'Peak intensity\s*=\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*\+/-\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*JY/BEAM\s*\(\s*(\d+\.\d+)\s*\)')
                    match = pattern.search(line)
                    if match:
                        summary['PEAK'] = float(match.group(1))
                        summary['PEAK_ERR'] = float(match.group(3))
                        summary['SNR'] = float(match.group(5))
                        continue
                    pattern = re.compile(r'RA\s+(\d+\s+\d+\s+\d+.\d+)\s+\+/-\s+(\d+.\d+)')
                    match = pattern.search(line)
                    if match:
                        summary['RA'] = match.group(1)
                        summary['RA_ERR'] = float(match.group(2))
                        continue
                    pattern = re.compile(r'DEC\s+([+-]?\d+\s+\d+\s+\d+.\d+)\s+\+/-\s+(\d+.\d+)')
                    match = pattern.search(line)
                    if match:
                        summary['DEC'] = match.group(1)
                        summary['DEC_ERR'] = float(match.group(2))
                        continue
                    pattern = re.compile(r'Major axis\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+asec')
                    match = pattern.search(line)
                    if match:
                        summary['MAJOR'] = float(match.group(1))
                        summary['MAJOR_ERR'] = float(match.group(2))
                        continue
                    pattern = re.compile(r'Minor axis\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+asec')
                    match = pattern.search(line)
                    if match:
                        summary['MINOR'] = float(match.group(1))
                        summary['MINOR_ERR'] = float(match.group(2))
                        continue
                    pattern = re.compile(r'Position angle\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+degrees')
                    match = pattern.search(line)
                    if match:
                        summary['PA'] = float(match.group(1))
                        summary['PA_ERR'] = float(match.group(2))
                        continue
                return summary
        except Exception as e:
            context.logger.error(f"Error in JMFIT summary: {e}")
            return {}
