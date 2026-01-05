import os

from core.Plugin import Plugin
from core.Context import Context


class CalibratorFitsExport(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Split and export FITS file for calibrators. Plugin SourceSelect must be run before. " \
               "Plugins required: AipsCatalog, GeneralTask, SourceSelect, CalibratorFringeFitting. " \
               "Parameter required: indisk; optional: for AIPS task SPLIT."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start calibrator FITS export")
        
        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        os.makedirs(targets_dir, exist_ok=True)
        for target in context.get_context().get("targets"):
            params_target = {"in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target)

            target_dir = os.path.join(targets_dir, target["NAME"])
            os.makedirs(target_dir, exist_ok=True)
            calibrator_dir = os.path.join(target_dir, "calibrators")
            os.makedirs(calibrator_dir, exist_ok=True)
            for calibrator in target["CALIBRATORS"]:
                params_split = {"inname": target["NAME"],
                          "inclass": "SPLAT",
                          "indisk": self.params["indisk"],
                          "inseq": params_target["inseq"],
                          "cl_source": f"CLCAL(FRING({calibrator['NAME']}))"}
                context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, params_split, "CL", "gainuse")
                task_split = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "SPLIT",
                                                                                     "inname": target["NAME"],
                                                                                     "inclass": "SPLAT",
                                                                                     "indisk": self.params["indisk"],
                                                                                     "inseq": params_target["inseq"],
                                                                                     "sources": [calibrator["NAME"]],
                                                                                     "docalib": 1,
                                                                                     "gainuse": params_split["gainuse"],
                                                                                     "aparm": self.params["aparm"],
                                                                                     "outdisk": self.params["indisk"]})
                task_split.run(context)
                if not context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context,
                                                                                          calibrator["NAME"],
                                                                                          "SPLIT",
                                                                                          self.params["indisk"],
                                                                                          f"{calibrator['NAME']} SELFCAL MAPPING",
                                                                                          history="Created by SPLIT"):
                    return False
                context.logger.info(f"Calibrator {calibrator['NAME']} SPLIT done")

                params_fittp = {"in_cat_ident": f"{calibrator['NAME']} SELFCAL MAPPING"}
                context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_fittp)
                fits_dir = os.path.join(calibrator_dir, f"{calibrator['NAME']}_FITTP.fits")
                task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "FITTP",
                                                                                     "inname": calibrator["NAME"],
                                                                                     "inclass": "SPLIT",
                                                                                     "indisk": self.params["indisk"],
                                                                                     "inseq": params_fittp["inseq"],
                                                                                     "dataout": fits_dir})
                task_fittp.run(context)
                context.logger.info(f"Calibrator {calibrator['NAME']} FITTP done")

        context.logger.info(f"Calibrator FITS export finished")
        return True
