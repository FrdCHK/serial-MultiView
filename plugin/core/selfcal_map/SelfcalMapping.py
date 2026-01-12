import os

from core.Plugin import Plugin
from core.Context import Context


class SelfcalMapping(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Call difmap to clean and self calibrate the target maps. Plugins SelfcalFitsExport must be run before. " \
        "Plugins required: SelfcalFitsExport, Difmap."
    
    def run(self, context: Context) -> bool:
        # TODO : add adjustable parameters from config & progress log info
        context.logger.info(f"Start target mapping with Difmap")
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        for target in context.get_context().get("targets"):
            target_dir = os.path.join(targets_dir, target["NAME"])
            context.get_context()["loaded_plugins"]["Difmap"].map(context, target_dir, target["NAME"])

        context.logger.info(f"Target mapping finished")
        return True
