from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Apcal(Plugin):
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.task = AIPSTask("APCAL")

    @classmethod
    def get_description(cls) -> str:
        return "Task to generate a SN table containing amplitude gain calibration information from a system temperature (TY) table and a gain curve GC table. " \
               "Plugin required: AipsCatalog. " \
               "Parameters required: inname, inclass, indisk, in_cat_ident, identifier."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task APCAL")

        context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)

        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "SN",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task APCAL finished")        
        return True
