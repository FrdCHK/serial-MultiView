"""
Prepare calibrator structure models for MultiView.
@Author: Jingdong Zhang
@DATE  : 2026/03/19
"""
import os

from core.Plugin import Plugin
from core.Context import Context


class MVCalibratorStructurePrepare(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Prepare source structure models for calibrators in each target. " \
               "For each calibrator: FRING + CLCAL, then SPLIT + FITTP to target/<target>/struc/<calibrator>_fittp.fits, " \
               "then run difmap and save target/<target>/struc/<calibrator>_selfcal.fits. " \
               "Plugins required: AipsCatalog, Fring, Clcal, GeneralTask, Difmap, MVPrimaryCalibratorSelect. " \
               "Parameters required: indisk, aparm, dparm, solint, opcode, interpol, smotyp, bparm; optional: cl_source, docalib, split_aparm."

    def run(self, context: Context) -> bool:
        context.logger.info("Start preparing calibrator structure models")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False

        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        os.makedirs(targets_dir, exist_ok=True)

        for target in context.get_context().get("targets"):
            params_target = {"in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
            if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target):
                context.logger.error(f"Target SPLAT catalog not found for {target['NAME']}")
                return False

            target_dir = os.path.join(targets_dir, target["NAME"])
            struc_dir = os.path.join(target_dir, "struc")
            os.makedirs(struc_dir, exist_ok=True)

            for calibrator in target.get("CALIBRATORS", []):
                calibrator_name = calibrator["NAME"]
                cl_source = self.params.get("cl_source", "SPLAT")

                task_fring = context.get_context()["loaded_plugins"]["Fring"]({
                    "inname": target["NAME"],
                    "inclass": "SPLAT",
                    "indisk": self.params["indisk"],
                    "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                    "calsour": [calibrator_name],
                    "timerang": [0],
                    "refant": context.get_context()["ref_ant"]["ID"],
                    "aparm": self.params["aparm"],
                    "dparm": self.params["dparm"],
                    "solint": self.params["solint"],
                    "docalib": self.params.get("docalib", -1),
                    "cl_source": cl_source,
                    "identifier": f"FRING({calibrator_name})",
                })
                if not task_fring.run(context):
                    return False

                task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({
                    "inname": target["NAME"],
                    "inclass": "SPLAT",
                    "indisk": self.params["indisk"],
                    "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                    "calsour": [calibrator_name],
                    "opcode": self.params["opcode"],
                    "interpol": self.params["interpol"],
                    "smotyp": self.params["smotyp"],
                    "bparm": self.params["bparm"],
                    "sn_source": f"FRING({calibrator_name})",
                    "cl_source": cl_source,
                    "identifier": f"CLCAL(FRING({calibrator_name}))",
                })
                if not task_clcal.run(context):
                    return False

                params_export = {
                    "inname": target["NAME"],
                    "inclass": "SPLAT",
                    "indisk": self.params["indisk"],
                    "inseq": params_target["inseq"],
                    "cl_source": f"CLCAL(FRING({calibrator_name}))",
                }
                if not context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, params_export, "CL", "gainuse"):
                    return False

                split_identifier = f"{calibrator_name} STRUC FITTP"
                task_split = context.get_context()["loaded_plugins"]["GeneralTask"]({
                    "task_name": "SPLIT",
                    "inname": target["NAME"],
                    "inclass": "SPLAT",
                    "indisk": self.params["indisk"],
                    "inseq": params_target["inseq"],
                    "sources": [calibrator_name],
                    "docalib": 1,
                    "gainuse": params_export["gainuse"],
                    "aparm": self.params.get("split_aparm", [2, 0]),
                    "outdisk": self.params["indisk"],
                })
                if not task_split.run(context):
                    return False

                if not context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(
                    context,
                    calibrator_name,
                    "SPLIT",
                    self.params["indisk"],
                    split_identifier,
                    history="Created by SPLIT for structure correction",
                ):
                    return False

                params_split = {"in_cat_ident": split_identifier}
                if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_split):
                    return False

                task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({
                    "task_name": "FITTP",
                    "inname": calibrator_name,
                    "inclass": "SPLIT",
                    "indisk": self.params["indisk"],
                    "inseq": params_split["inseq"],
                    "dataout": os.path.join(struc_dir, f"{calibrator_name}_fittp.fits"),
                })
                if not task_fittp.run(context):
                    return False

                if not context.get_context()["loaded_plugins"]["Difmap"].map(
                    context,
                    struc_dir,
                    calibrator_name,
                    suffix="_fittp.fits",
                ):
                    return False
                context.logger.info(f"Calibrator {calibrator_name} structure model prepared for target {target['NAME']}")

        context.logger.info("Calibrator structure model preparation finished")
        return True
