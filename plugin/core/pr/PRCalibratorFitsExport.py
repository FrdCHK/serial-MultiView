import os

from core.Plugin import Plugin
from core.Context import Context


class PRCalibratorFitsExport(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Split and export FITS file for calibrators. Plugins SourceSelect and PRCalibratorFringeFitting must be run before. " \
               "Plugins required: AipsCatalog, GeneralTask, SourceSelect, PRCalibratorFringeFitting. " \
               "Parameter required: indisk; optional: aparm for AIPS task SPLIT."
    
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
                if not context.get_context()["loaded_plugins"]["FitsExport"].export(context,
                                                                                    target["NAME"],
                                                                                    "SPLAT",
                                                                                    self.params["indisk"],
                                                                                    params_target["inseq"],
                                                                                    params_split["gainuse"],
                                                                                    calibrator["NAME"],
                                                                                    calibrator_dir,
                                                                                    self.params["aparm"] if "aparm" in self.params else [0]):
                    context.logger.info(f"Error in calibrator FITS export")
                    return False

        context.logger.info(f"Calibrator FITS export finished")
        return True
