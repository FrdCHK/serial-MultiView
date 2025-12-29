from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task
from .source2ver import source2ver


class Clcor(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, indisk, inseq, opcode, cl_source, identifier must be specified"""
        self.params = params
        for _, v in self.params.items():
            if isinstance(v, list):
                v.insert(0, None)
        self.task = AIPSTask("CLCOR")

    @classmethod
    def get_description(cls) -> str:
        return "Task to make a number of different corrections to a CL table."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task CLCOR")

        # search for gainver
        if not source2ver(context, self.params, "CL"):
            return False

        run_task(self.task, self.params)
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "CL",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task CLCOR finished")        
        return True
