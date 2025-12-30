import pandas as pd
import yaml
from typing import Dict, Any

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
        return "Select target and calibrator sources. Plugin required: GeneralTask, AipsCalog."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start selecting sources")
        
        if self.params.get("load", None):
            # load sources from file (context of another experiment)
            try:
                with open(self.params["load"], 'r') as f:
                    predef = yaml.safe_load(f)
            except Exception as e:
                context.logger.warning(f"Failed to load predef source list file {self.params['load']}: {e}")
                context.logger.info(f"Continue with manual selection")
            else:
                predef_targets = predef.get("targets", [])
                if predef_targets:
                    context.edit_context({"targets": predef_targets})
                    context.logger.info(f"Predef source list file {self.params['load']} loaded successfully")
                    return True
                else:
                    context.logger.warning(f"Predef source list file {self.params['load']} does not contain targets")
                    context.logger.info(f"Continue with manual selection")
            # if encounter error, just catch and log it and continue with manual selection
        
        sources = pd.DataFrame(context.get_context()["sources"])
        target_num = integer_input("Please input the number of targets", 1)
        selected_sources = []  # to avoid duplicates
        targets = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
        context.edit_context({"targets": []})
        for i in range(target_num):
            print("\033[34mSource list:")
            print(sources[["ID", "NAME"]].to_string(index=False)+"\033[0m")
            while True:
                while True:
                    target_id = integer_input(f"Target {i+1} ID")
                    if target_id in range(1, sources.index.size+1):
                        break
                    else:
                        print("\033[31mInvalid input!\033[0m")
                if target_id in selected_sources:
                    print("\033[31mSource already selected!\033[0m")
                else:
                    selected_sources.append(target_id)
                    targets.loc[targets.index.size] = (sources.loc[sources["ID"] == target_id]).iloc[0]
                    break
            target_item = {"ID": int(targets.loc[i, "ID"]), "NAME": str(targets.loc[i, "NAME"]),
                             "RA": float(targets.loc[i, "RA"]), "DEC": float(targets.loc[i, "DEC"])}

            # select calibrators for each target
            calibrators = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
            while True:
                redo_flag = False
                user_input = input(f"Target {i+1} calibrator IDs (space separated): ")
                parts = user_input.split()
                parts = list(dict.fromkeys(parts))  # remove duplicates
                for part in parts:
                    if is_integer(part):
                        int_part = int(part)
                        if not (int_part in range(1, sources.index.size+1)):
                            print("\033[31mInvalid input!\033[0m")
                            redo_flag = True
                            break
                    else:
                        print("\033[31mInvalid input!\033[0m")
                        redo_flag = True
                        break
                if redo_flag:
                    continue
                for part in parts:
                    int_part = int(part)
                    calibrators.loc[calibrators.index.size] = (sources.loc[sources["ID"] == int_part]).iloc[0]
                break
            target_item["CALIBRATORS"] = calibrators.to_dict()
            context.get_context()["targets"].append(target_item)

        context.logger.info(f"Sources selected")
        return True
