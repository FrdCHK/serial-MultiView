from core.Plugin import Plugin
from core.Context import Context


class SelfcalFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fitting for all targets. Plugin SelfcalSourceSelect must be run before." \
               "Plugins required: AipsCatalog, Fring, Clcal, SelfcalSourceSelect. " \
               "Parameter required: indisk, aparm, dparm, solint, opcode, interpol, smotyp, bparm."

    def run(self, context: Context) -> bool:
        context.logger.info("Start selfcal fringe fitting")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False
        for target in context.get_context().get("targets"):
            task_fring = context.get_context()["loaded_plugins"]["Fring"]({"inname": target["NAME"],
                                                                           "inclass": "SPLAT",
                                                                           "indisk": self.params["indisk"],
                                                                           "in_cat_ident": f"{target['NAME']}",
                                                                           "calsour": [target["NAME"]],
                                                                           "timerang": [0],
                                                                           "refant": context.get_context()["ref_ant"]["ID"],
                                                                           "aparm": self.params["aparm"],
                                                                           "dparm": self.params["dparm"],
                                                                           "solint": self.params["solint"],
                                                                           "docalib": -1,
                                                                           "identifier": f"FRING({target['NAME']})"})
            task_fring.run(context)
            task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({"inname": target["NAME"],
                                                                           "inclass": "SPLAT",
                                                                           "indisk": self.params["indisk"],
                                                                           "in_cat_ident": f"{target['NAME']}",
                                                                           "calsour": [target["NAME"]],
                                                                           "sources": [target["NAME"]],
                                                                           "opcode": self.params["opcode"],
                                                                           "interpol": self.params["interpol"],
                                                                           "smotyp": self.params["smotyp"],
                                                                           "bparm": self.params["bparm"],
                                                                           "sn_source": f"FRING({target['NAME']})",
                                                                           "cl_source": "SPLAT",
                                                                           "identifier": f"CLCAL(FRING({target['NAME']}))"})
            task_clcal.run(context)
            context.logger.info(f"Target {target['NAME']} fringe fitting done")

        context.logger.info("Selfcal fringe fitting finished")
        return True
