from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Fring(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, indisk, inseq, identifier must be specified"""
        self.params = params
        self.task = AIPSTask("FRING")

    @classmethod
    def get_description(cls) -> str:
        return "Task to fringe fit data."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task FRING")

        # search for gainuse
        if ("cl_source" in self.params) and (not context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, self.params, "CL", "gainuse")):
            return False

        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "SN", ext_source=self.params["identifier"])
        context.logger.info("AIPS task FRING finished")
        return True
