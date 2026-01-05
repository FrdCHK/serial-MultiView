from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Fitld(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """outname and outclass must be specified"""
        self.params = params
        self.task = AIPSTask("FITLD")

    @classmethod
    def get_description(cls) -> str:
        return "Task to store an image or UV data from a FITS tape. " \
               "Plugin required: AipsCatalog. " \
               "Parameters required: datain, outname, outclass, out_cat_ident."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task FITLD")

        if "out_cat_ident" in self.params:
            out_cat_ident = self.params["out_cat_ident"]
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params, "out_cat_ident", "outseq")

        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context,
                                                                           self.params["outname"],
                                                                           self.params["outclass"],
                                                                           self.params["outdisk"] if "outdisk" in self.params else 1,
                                                                           out_cat_ident,
                                                                           history=self.params["history"] if "history" in self.params else "Created by FITLD")
        context.logger.info("AIPS task FITLD finished")
        return True
