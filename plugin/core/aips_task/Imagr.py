from typing import Dict, Any
from AIPSTask import AIPSTask
import AIPSTV

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Imagr(Plugin):
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.task = AIPSTask("IMAGR")

    @classmethod
    def get_description(cls) -> str:
        return "Wide field imaging/Clean task. " \
               "Plugin required: AipsCatalog. " \
               "Parameters required: inname, inclass, indisk, in_cat_ident, out_cat_ident."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task IMAGR")

        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)
        if "out_cat_ident" in self.params:
            out_cat_ident = self.params["out_cat_ident"]
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params, "out_cat_ident", "outseq")

        tv = AIPSTV.AIPSTV()
        if not tv.exists():
            tv.start()
        self.params["tv"] = tv
        if not run_task(self.task, self.params, context):
            return False
        if tv.exists():
            tv.kill()
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context,
                                                                           self.params["inname"],
                                                                           "IBM001",
                                                                           self.params["indisk"],
                                                                           out_cat_ident,
                                                                           history=self.params["history"] if "history" in self.params else "Created by IMAGR")
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context,
                                                                           self.params["inname"],
                                                                           "ICL001",
                                                                           self.params["indisk"],
                                                                           out_cat_ident,
                                                                           history=self.params["history"] if "history" in self.params else "Created by IMAGR")
        context.logger.info("AIPS task IMAGR finished")
        return True
