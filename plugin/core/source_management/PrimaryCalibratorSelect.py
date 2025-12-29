import pandas as pd
from typing import Dict, Any, Tuple
from AIPSData import AIPSUVData
import AIPSTV

from core.Plugin import Plugin
from core.Context import Context
from util.integer_input import integer_input, is_integer


class SourceSelect(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """
        initiate the plugin
        :param params: parameters for the plugin
        """
        self.params = params

    @classmethod
    def get_description(cls) -> str:
        return "Select primary calibrator."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start selecting primary calibrator")
        # TODO: select primary calibrator
        context.logger.info(f"Primary calibrator selected")
        return True
        
    def possm(self, context: Context, calibrator_list: pd.DataFrame) -> bool:
        try:
            tv = AIPSTV.AIPSTV()
            if not tv.exists():
                tv.start()
            highst_cl_ver = context.get_context()["loaded_plugins"]["AipsCatalog"].get_highest_ext_ver(context,
                                                                                                       self.params["inname"],
                                                                                                       self.params["inclass"],
                                                                                                       self.params["indisk"],
                                                                                                       self.params["inseq"],
                                                                                                       "CL")
            task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "POSSM",
                                                                           "inname": self.params["inname"],
                                                                           "inclass": self.params["inclass"],
                                                                           "indisk": self.params["indisk"],
                                                                           "inseq": self.params["inseq"],
                                                                           "sources": calibrator_list,
                                                                           "aparm": [0, 1, 0, 0, -180, 180, 0, 0, 1],
                                                                           "dotv": 1,
                                                                           "tv": tv,
                                                                           "nplots": 9,
                                                                           "docalib": 1,
                                                                           "gainuse": highst_cl_ver,
                                                                           "stokes": "I",
                                                                           "solint": -1})
            task.run(context)
        except:
            return False
        else:
            input("Press enter to continue...")
            if tv.exists():
                tv.kill()
            return True
