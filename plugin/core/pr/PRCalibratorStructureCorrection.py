import os

from core.Plugin import Plugin
from core.Context import Context


class PRCalibratorStructureCorrection(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Apply source structure correction for calibrators. Plugins PRCalibratorMapping must be run before. " \
               "Plugins required: AipsCatalog, GeneralTask, SourceSelect, PRCalibratorMapping. " \
               "Parameter required: indisk; optional: aparm for AIPS task SPLIT."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start calibrator source structure correction")
        
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
            calibrator_dir = os.path.join(target_dir, "calibrators")
            for calibrator in target["CALIBRATORS"]:
                map_identifier = f"DIFMAP({calibrator['NAME']})"
                task_fitld = context.get_context()["loaded_plugins"]["Fitld"]({"datain": os.path.join(calibrator_dir, f"{calibrator['NAME']}_selfcal.fits"),
                                                                               "outname": calibrator['NAME'],
                                                                               "outclass": "ICLN",
                                                                               "out_cat_ident": map_identifier})
                task_fitld.run(context)

                calib_identifier = f"CALIB({calibrator['NAME']})"
                task_calib = context.get_context()["loaded_plugins"]["Calib"]({"inname": target["NAME"],
                                                                               "inclass": "SPLAT",
                                                                               "indisk": self.params["indisk"],
                                                                               "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                                                                               "calsour": [calibrator["NAME"]],
                                                                               "refant": context.get_context()["ref_ant"]["ID"],
                                                                               "docalib": 1,
                                                                               "cl_source": f"CLCAL(FRING({calibrator['NAME']}))",
                                                                               "solint": 9.999/60,
                                                                               "in2name": calibrator["NAME"],
                                                                               "in2class": "ICLN",
                                                                               "in2_cat_ident": map_identifier,
                                                                               "in2disk": self.params["indisk"],
                                                                               "cmethod": "DFT",
                                                                               "cmodel": "COMP",
                                                                               "normaliz": 1,
                                                                               "cparm": [0, 1],
                                                                               "identifier": calib_identifier})
                task_calib.run(context)

                task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({"inname": target["NAME"],
                                                                               "inclass": "SPLAT",
                                                                               "indisk": self.params["indisk"],
                                                                               "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                                                                               "calsour": [calibrator["NAME"]],
                                                                               "sn_source": calib_identifier,
                                                                               "cl_source": f"CLCAL(FRING({calibrator['NAME']}))",
                                                                               "identifier": calib_identifier})
                task_clcal.run(context)

        context.logger.info(f"Calibrator source structure correction finished")
        return True
