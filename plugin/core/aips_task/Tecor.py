from typing import Dict, Any
from AIPSTask import AIPSTask
from datetime import datetime, timedelta

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
        return "Task to derive corrections for ionospheric Faraday rotation and dispersive delay from maps of total electron content in IONEX format."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start AIPS task TECOR")
        d = context.get_context()["obs_time"]["date"]
        year = d.year
        doy = d.timetuple().tm_yday
        self.params["infile"] = f"jplg{doy:03d}0.{year % 2000:02d}i"
        self.params["nfiles"] = context.get_context()["obs_time"]["day_num"]
        run_task(self.task, self.params)
        context.get_context()["loaded_plugins"]["AipsCatalog"].add_ext(context,
                                                                       self.params["inname"],
                                                                       self.params["inclass"],
                                                                       self.params["indisk"],
                                                                       self.params["inseq"],
                                                                       "CL",
                                                                       ext_source=self.params["identifier"])
        context.logger.info("AIPS task TECOR finished")        
        return True
