from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Clcal(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, indisk, inseq, sn_source, identifier must be specified"""
        self.params = params
        self.task = AIPSTask("CLCAL")

    @classmethod
    def get_description(cls) -> str:
        return "Task to applie solutions from a set of SN tables to selected entries in one CL table and writes them into another CL table."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task CLCAL")
        ext_search_result = context.get_context()["loaded_plugins"]["AipsCatalog"].search_ext(context,
                                                                                              self.params["inname"],
                                                                                              self.params["inclass"],
                                                                                              self.params["indisk"],
                                                                                              self.params["inseq"],
                                                                                              "SN",
                                                                                              ext_source=self.params["sn_source"])
        if not ext_search_result["status"]:
            return False
        self.params["snver"] = context.get_context()["aips_catalog"][ext_search_result["cat_index"]]["ext"][ext_search_result["ext_index"]]["version"][ext_search_result["ver_index"]]["num"]
        self.params.pop("sn_source")
        run_task(self.task, self.params)
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "CL",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task CLCAL finished")        
        return True
