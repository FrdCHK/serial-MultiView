import pandas as pd

from core.Context import Context
from util.integer_input import integer_input, is_integer
from .SourceSelect import SourceSelect


class SelfcalSourceSelect(SourceSelect):
    @classmethod
    def get_description(cls) -> str:
        return "Select target sources for self-calibration mapping experiment. " \
        "Plugins required: SourceSelect, GetObsInfo."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start selecting selfcal sources")

        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)
        
        predef_load_status = self.predef_load(context)
        if predef_load_status == -1:
            context.logger.error(f"Error in SelfcalSourceSelect")
            return False
        elif predef_load_status == 0:
            context.logger.info(f"Selfcal source selection finished")
            return True
        
        sources = pd.DataFrame(context.get_context()["sources"])
        print("\033[34mSource list:")
        print(sources[["ID", "NAME"]].to_string(index=False)+"\033[0m")
        
        targets_df = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
        while True:
            redo_flag = False
            user_input = input(f"Target IDs (space separated): ")
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
                targets_df.loc[targets_df.index.size] = (sources.loc[sources["ID"] == int_part]).iloc[0]
            break
        targets_dict = targets_df.to_dict(orient='records')
        context.edit_context({"targets": targets_dict})

        context.logger.info(f"Selfcal source selection finished")

        if not self.splat(context):
            return False
        context.logger.info(f"Target SPLAT finished")

        return True
