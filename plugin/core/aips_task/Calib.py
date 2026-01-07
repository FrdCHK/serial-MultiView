from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Calib(Plugin):
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.task = AIPSTask("CALIB")

    @classmethod
    def get_description(cls) -> str:
        return "Task to determine calibration for data. " \
        "Plugin required: AipsCatalog. " \
        "Parameters required: inname, inclass, indisk, in_cat_ident, cl_source, identifier; optional: for AIPS tasks CALIB & CLCAL."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task CALIB")

        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)
        if "in2_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params, "in2_cat_ident", "in2seq")

        # search for gainuse
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, self.params, "CL", "gainuse"):
            return False
        
        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "SN",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task CALIB finished")        
        return True
