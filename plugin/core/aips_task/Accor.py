from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Accor(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, indisk, inseq, identifier must be specified"""
        self.params = params
        self.task = AIPSTask("ACCOR")

    @classmethod
    def get_description(cls) -> str:
        return "Task to correct amplitudes in cross-correlation spectra due to errors in sampler thresholds."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task ACCOR")
        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "SN", ext_source=self.params["identifier"])
        context.logger.info("AIPS task ACCOR finished")        
        return True
