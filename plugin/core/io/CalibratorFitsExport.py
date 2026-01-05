import os

from core.Plugin import Plugin
from core.Context import Context


class CalibratorFitsExport(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Split and export FITS file for calibrators. Plugin required: AipsCatalog, GeneralTask, SourceSelect, CalibratorSelfCalibration."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start calibrator FITS export")
        
        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        os.makedirs(targets_dir, exist_ok=True)
        for target in context.get_context().get("targets"):
            target_dir = os.path.join(targets_dir, target["NAME"])
            os.makedirs(target_dir, exist_ok=True)
            calibrator_dir = os.path.join(target_dir, "calibrators")
            os.makedirs(calibrator_dir, exist_ok=True)
            for calibrator in target["CALIBRATORS"]:
                params = {"inname": target["NAME"],
                          "inclass": "SPLAT",
                          "indisk": self.params["indisk"],
                          "inseq": 1,
                          "cl_source": f"CLCAL(FRING({calibrator['NAME']}))"}
                context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, params, "CL", "gainuse")
                task_split = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "SPLIT",
                                                                                     "inname": target["NAME"],
                                                                                     "inclass": "SPLAT",
                                                                                     "indisk": self.params["indisk"],
                                                                                     "inseq": 1,
                                                                                     "sources": [calibrator["NAME"]],
                                                                                     "docalib": 1,
                                                                                     "gainuse": params["gainuse"],
                                                                                     "aparm": self.params["aparm"],
                                                                                     "outdisk": self.params["indisk"],
                                                                                     "outseq": 1})
                task_split.run(context)
                if not context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context, calibrator["NAME"], "SPLIT", self.params["indisk"], 1, "Created by SPLIT"):
                    return False
                context.logger.info(f"Calibrator {calibrator['NAME']} SPLIT done")

                fits_dir = os.path.join(calibrator_dir, f"{calibrator['NAME']}_FITTP.fits")
                task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "FITTP",
                                                                                     "inname": calibrator["NAME"],
                                                                                     "inclass": "SPLIT",
                                                                                     "indisk": self.params["indisk"],
                                                                                     "inseq": 1,
                                                                                     "dataout": fits_dir})
                task_fittp.run(context)
                context.logger.info(f"Calibrator {calibrator['NAME']} FITTP done")

        context.logger.info(f"Calibrator FITS export finished")
        return True
