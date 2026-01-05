from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Clcor(Plugin):
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.task = AIPSTask("CLCOR")

    @classmethod
    def get_description(cls) -> str:
        return "Task to make a number of different corrections to a CL table. " \
               "Plugin required: AipsCatalog. " \
               "Parameters required: inname, inclass, indisk, in_cat_ident, opcode, identifier."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task CLCOR")

        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)

        # search for gainver
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, self.params, "CL"):
            return False

        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "CL",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task CLCOR finished")        
        return True
