from typing import Dict, Any, Tuple
from AIPSData import AIPSUVData
import AIPSTV

from core.Plugin import Plugin
from core.Context import Context
from util.yes_no_input import yes_no_input


class RefAntSelect(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """
        initiate the plugin
        :param params: parameters for the plugin
        """
        self.params = params

    @classmethod
    def get_description(cls) -> str:
        return "Select reference antenna. Plugin required: GeneralTask."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start selecting reference antenna")
        
        if self.params["auto_ref_ant"]:
            # auto selection
            default_vlba_ref_ant = ["PT", "FD", "KP"]
            data = AIPSUVData(self.params["inname"], self.params["inclass"], int(self.params["indisk"]), int(self.params["inseq"]))
            ty_exist = False
            for item in data.tables:
                if item[1] == "AIPS TY":
                    ty_exist = True
                    break
            if ty_exist:
                ty_table = data.table("AIPS TY", 0)
                for item in default_vlba_ref_ant:
                    for ant in context.get_context()["antennas"]:
                        if item == ant["NAME"]:
                            ant_id = ant["ID"]
                            break
                    high_tsys_flag = False
                    for ty_row in ty_table:
                        if ty_row['antenna_no'] == ant_id and (any(tsys > 40. for tsys in ty_row['tsys_1']) or 
                                                               (context.get_context()["no_if"] > 1 and any(tsys > 40. for tsys in ty_row['tsys_2']))):
                            high_tsys_flag = True
                            context.logger.debug(f"High system temprature detected: antenna {ant_id} {item}")
                            break
                    if not high_tsys_flag:
                        context.edit_context({'ref_ant': {'ID': ant_id, 'NAME': item}})
                        context.logger.info(f"Reference antenna {ant_id} {item} selected")
                        return True
                context.logger.info(f"System temperature issue for auto selection list, manual selection start")

            if not self.select_ref_ant(context):
                context.logger.error(f"Reference antenna selection failed")
                return False
        else:
            if self.params["ref_ant"].casefold() in [item["NAME"].casefold() for item in context.get_context()["antennas"]]:
                for item in context.get_context()["antennas"]:
                    if item["NAME"].casefold() == self.params["ref_ant"].casefold():
                        context.edit_context({'ref_ant': {'ID': item["ID"], 'NAME': item["NAME"]}})
                        break
                context.logger.info(f"Reference antenna specified in config: {context.get_context()['ref_ant']['NAME']}")
                return True
            else:
                context.logger.warning(f"Reference antenna specified in config {context.get_context()['config']['ref_ant'].upper()} is not available, manual selection start")
                if not self.select_ref_ant(context):
                    context.logger.error(f"Reference antenna selection failed")
                    return False
        context.logger.info(f"Reference antenna {context.get_context()['ref_ant']['ID']} {context.get_context()['ref_ant']['NAME']} selected")
        return True
    
    def select_ref_ant(self, context: Context) -> bool:
        ty_exist = False
        wx_exist = False
        data = AIPSUVData(self.params["inname"], self.params["inclass"], int(self.params["indisk"]), int(self.params["inseq"]))
        for item in data.tables:
            if item[1] == "AIPS TY":
                ty_exist = True
            elif item[1] == "AIPS WX":
                wx_exist = True
            elif ty_exist and wx_exist:
                break
        if ty_exist and yes_no_input("Do you wish to plot system temprature (TY table)?", False):
            if not self.plot_ty(context):
                context.logger.error(f"TY plot failed")
                return False
        if wx_exist and yes_no_input("Do you wish to plot weather log (WX table)?", False):
            if not self.plot_wx(context):
                context.logger.error(f"WX plot failed")
                return False
        ant_id, ant_name = self.ant_input(context)
        context.edit_context({'ref_ant': {'ID': ant_id, 'NAME': ant_name}})
        return True
        
    def plot_ty(self, context: Context) -> bool:
        try:
            tv = AIPSTV.AIPSTV()
            if not tv.exists():
                tv.start()
            task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "SNPLT",
                                                                            "inname": self.params["inname"],
                                                                            "inclass": self.params["inclass"],
                                                                            "indisk": self.params["indisk"],
                                                                            "inseq": self.params["inseq"],
                                                                            "inext": "TY",
                                                                            "dotv": 1,
                                                                            "optype": "TSYS",
                                                                            "opcode": "ALSI",
                                                                            "do3color": 1})
            task.run(context)
        except:
            return False
        else:
            input("Press enter to continue...")
            if tv.exists():
                tv.kill()
            return True

    def plot_wx(self, context: Context) -> bool:
        no_antenna = len(context.get_context()["antennas"])
        try:
            tv = AIPSTV.AIPSTV()
            if not tv.exists():
                tv.start()
            while True:
                user_input = input("Select OPTYPE (TEMP/PRES/DEWP/WGUS/PREC or other available types) or QUIT to finish: ")
                if user_input.casefold() in ['temp', 'pres', 'dewp', 'wvel', 'wdir', 'wgus', 'prec', 'h2oc', 'ionc', 'rhum', 'ch2o', 'kzop', 'qzop', 'wcos', 'wsin', 'ddep']:
                    task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "WETHR",
                                                                                   "inname": self.params["inname"],
                                                                                   "inclass": self.params["inclass"],
                                                                                   "indisk": self.params["indisk"],
                                                                                   "inseq": self.params["inseq"],
                                                                                   "inext": "TY",
                                                                                   "dotv": 1,
                                                                                   "optype": user_input.upper(),
                                                                                   "opcode": "ALSI",
                                                                                   "do3color": 1,
                                                                                   "nplots": no_antenna})
                    task.run(context)
                elif user_input.casefold() == "quit":
                    break
                else:
                    print("\033[31mInvalid input!\033[0m")
            
        except:
            return False
        else:
            if tv.exists():
                tv.kill()
            return True
    
    @classmethod
    def ant_input(cls, context: Context) -> Tuple[int, str]:
        print("\033[32mSelect a reference antenna in the available antennas:\033[0m")
        for item in context.get_context()["antennas"]:
            print(f"\033[32m{item['ID']} {item['NAME']}\033[0m")
        while True:
            user_input = input("Enter antenna ID or NAME: ")
            if user_input.isdigit():
                if int(user_input) in [item["ID"] for item in context.get_context()["antennas"]]:
                    for item in context.get_context()["antennas"]:
                        if item["ID"] == int(user_input):
                            return item["ID"], item["NAME"]
            elif user_input.casefold() in [item["NAME"].casefold() for item in context.get_context()["antennas"]]:
                for item in context.get_context()["antennas"]:
                    if item["NAME"].casefold() == user_input.casefold():
                        return item["ID"], item["NAME"]
            print("\033[31mInvalid input!\033[0m")
