import os

from core.Plugin import Plugin
from core.Context import Context


class PRCalibratorMapping(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Call difmap to clean and self calibrate the calibrator maps. Plugins PRFitsExport must be run before. " \
        "Plugins required: PRCalibratorFitsExport, Difmap."
    
    def run(self, context: Context) -> bool:
        # TODO : add adjustable parameters from config & progress log info
        context.logger.info(f"Start calibrator mapping with Difmap")
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        for target in context.get_context().get("targets"):
            target_dir = os.path.join(targets_dir, target["NAME"])
            calibrators_dir = os.path.join(target_dir, "calibrators")
            for calibrator in target["CALIBRATORS"]:
                context.get_context()["loaded_plugins"]["Difmap"].map(context, calibrators_dir, calibrator["NAME"])

        context.logger.info(f"Calibrator mapping finished")
        return True
