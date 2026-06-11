"""
Construct Target object in context for manual sMV.
@Author: Jingdong Zhang
@DATE  : 2026/06/11
"""
import os
import math
import yaml
import pandas as pd
from typing import Dict, Any
from AIPSData import AIPSUVData

from core.Plugin import Plugin
from core.Context import Context
from util.yaml_util import safe_dump_builtin


class ManualTargetConstruct(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Construct Target object in context for manual sMV. " \
               "Plugins required: AipsCatalog, PRCalibratorFringeFitting. " \
               "Parameters required: indisk."

    def run(self, context: Context) -> bool:
        context.logger.info("Start Target object construction for manual sMV")

        sources = pd.DataFrame(context.get_context().get("sources", []))
        targets = []
        for item in context.get_context().get("config").get("target"):
            target = sources.loc[sources['NAME'] == item.get("name")]
            tmp_dict = {"NAME": item.get("name"),
                        "ID": int(target["ID"].values[0]),
                        "RA": float(target["RA"].values[0]),
                        "DEC": float(target["DEC"].values[0]),
                        "INNAME": item.get("inname"),
                        "INCLASS": item.get("inclass"),
                        "INDISK": int(item.get("indisk")),
                        "INSEQ": int(item.get("inseq")),
                        "SN_MV": int(item.get("sn_mv")),
                        "CALIBRATORS": []}
            for calsour in item.get("calibrators"):
                cal = sources.loc[sources['NAME'] == calsour.get("name")]
                cal_dict = {"NAME": calsour.get("name"),
                            "ID": int(cal["ID"].values[0]),
                            "RA": float(cal["RA"].values[0]),
                            "DEC": float(cal["DEC"].values[0]),
                            "SN": calsour.get("sn")}
                tmp_dict["CALIBRATORS"].append(cal_dict)
            primary_cal = sources.loc[sources['NAME'] == item.get("primary_calibrator").get("name")]
            tmp_dict["primary_calibrator"] = {"NAME": item.get("primary_calibrator").get("name"),
                                              "ID": int(primary_cal["ID"].values[0]),
                                              "RA": float(primary_cal["RA"].values[0]),
                                              "DEC": float(primary_cal["DEC"].values[0]),
                                              "SN": item.get("primary_calibrator").get("sn")}
            targets.append(tmp_dict)
        context.edit_context({"targets": targets})

        context.logger.info("Target object construction finished")
        return True
