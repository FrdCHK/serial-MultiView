from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task
from .source2ver import source2ver


class Fring(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, indisk, inseq, identifier must be specified"""
        self.params = params
        for _, v in self.params.items():
            if isinstance(v, list):
                v.insert(0, None)
        self.task = AIPSTask("FRING")

    @classmethod
    def get_description(cls) -> str:
        return "Task to fringe fit data."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task FRING")

        # search for gainuse
        if not source2ver(context, self.params, "CL", "gainuse"):
            return False
        
        # replace default parameter values
        if "calsour" in self.params and self.params["calsour"] == "$MPC_AUTO$":
            self.params["calsour"] = [None, context.get_context()["mpc_calsour"]["name"]]
        if "timerang" in self.params and self.params["timerang"] == "$MPC_AUTO$":
            first_scan_end_time = context.get_context()["mpc_calsour"]["end_time"]
            self.params["timerang"] = [None, 0, 0, 0, 0, first_scan_end_time["day"], first_scan_end_time["hour"], first_scan_end_time["minute"], first_scan_end_time["second"]]
        if "refant" in self.params and self.params["refant"] == "$DEFAULT$":
            self.params["refant"] = context.get_context()["ref_ant"]["ID"]

        run_task(self.task, self.params)
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "SN", ext_source=self.params["identifier"])
        context.logger.info("AIPS task FRING finished")        
        return True
