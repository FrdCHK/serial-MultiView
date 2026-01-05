from typing import Dict, Any
from AIPSTask import AIPSTask
import os

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class Tecor(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, indisk, inseq, identifier must be specified"""
        self.params = params
        self.task = AIPSTask("TECOR")

    @classmethod
    def get_description(cls) -> str:
        return "Task to derive corrections for ionospheric Faraday rotation and dispersive delay from maps of total electron content in IONEX format. " \
               "Plugins required: AipsCatalog, GetObsInfo. " \
               "Parameters required: inname, inclass, indisk, in_cat_ident, cl_source, identifier."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task TECOR")

        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)

        d = context.get_context()["obs_time"]["date"]
        year = d.year
        doy = d.timetuple().tm_yday
        self.params["infile"] = os.path.join(context.get_context()["config"]["ionex_dir"], f"jplg{doy:03d}0.{year % 2000:02d}i")
        self.params["nfiles"] = context.get_context()["obs_time"]["day_num"]
        if not run_task(self.task, self.params, context):
            return False
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "CL",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task TECOR finished")        
        return True
