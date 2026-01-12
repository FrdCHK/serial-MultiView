import pandas as pd

from core.Context import Context
from util.integer_input import integer_input, is_integer
from .SourceSelect import SourceSelect


class PRSourceSelect(SourceSelect):
    @classmethod
    def get_description(cls) -> str:
        return "Select target and calibrator sources for Phase referencing experiment. " \
        "Plugins required: SourceSelect, GetObsInfo."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start selecting PR sources")

        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)
        
        predef_load_status = self.predef_load(context)
        if predef_load_status == -1:
            context.logger.error(f"Error in PRSourceSelect")
            return False
        elif predef_load_status == 0:
            context.logger.info(f"PR source selection finished")
            return True
        
        sources = pd.DataFrame(context.get_context()["sources"])
        while True:
            target_num = integer_input("Please input the number of targets", 1)
            if target_num > 0:
                break
            print("\033[31mTarget number should be > 0!\033[0m")
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
            target_item["CALIBRATORS"] = calibrators.to_dict(orient='records')
            context.get_context()["targets"].append(target_item)

        context.logger.info(f"PR source selection finished")

        if not self.splat(context):
            return False
        context.logger.info(f"Target & calibrators SPLAT finished")

        return True
