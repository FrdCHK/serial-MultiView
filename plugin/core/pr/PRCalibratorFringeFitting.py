from core.Plugin import Plugin
from core.Context import Context


class PRCalibratorFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fitting for all calibrators. Plugin SourceSelect must be run before." \
               "Plugins required: AipsCatalog, Fring, Clcal, SourceSelect. " \
               "Parameter required: indisk; optional: for AIPS task FRING & CLCAL."

    def run(self, context: Context) -> bool:
        context.logger.info("Start PR calibrator fringe fitting")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False
        for target in context.get_context().get("targets"):
            for calibrator in target["CALIBRATORS"]:
                task_fring = context.get_context()["loaded_plugins"]["Fring"]({"inname": target["NAME"],
                                                                               "inclass": "SPLAT",
                                                                               "indisk": self.params["indisk"],
                                                                               "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                                                                               "calsour": [calibrator["NAME"]],
                                                                               "timerang": [0],
                                                                               "refant": context.get_context()["ref_ant"]["ID"],
                                                                               "aparm": self.params["aparm"],
                                                                               "dparm": self.params["dparm"],
                                                                               "solint": self.params["solint"],
                                                                               "docalib": -1,
                                                                               "identifier": f"FRING({calibrator['NAME']})"})
                task_fring.run(context)
                task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({"inname": target["NAME"],
                                                                               "inclass": "SPLAT",
                                                                               "indisk": self.params["indisk"],
                                                                               "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                                                                               "calsour": [calibrator["NAME"]],
                                                                            #    "sources": [calibrator["NAME"]],  # apply to all sources should work for any scenario
                                                                               "opcode": self.params["opcode"],
                                                                               "interpol": self.params["interpol"],
                                                                               "smotyp": self.params["smotyp"],
                                                                               "bparm": self.params["bparm"],
                                                                               "sn_source": f"FRING({calibrator['NAME']})",
                                                                               "cl_source": "SPLAT",
                                                                               "identifier": f"CLCAL(FRING({calibrator['NAME']}))"})
                task_clcal.run(context)
                context.logger.info(f"Calibrator {calibrator['NAME']} fringe fitting done")

        context.logger.info("Calibrator fringe fitting finished")
        return True
