from core.Plugin import Plugin
from core.Context import Context


class CalibratorFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fitting for all calibrators. Plugin required: Fring. Plugin SourceSelect must be run before."

    def run(self, context: Context) -> bool:
        context.logger.info("Start calibrator fringe fitting")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False
        for target in context.get_context().get("targets"):
            for calibrator in target["CALIBRATORS"]:
                task_fring = context.get_context()["loaded_plugins"]["Fring"]({"inname": target["NAME"],
                                                                               "inclass": "SPLAT",
                                                                               "indisk": self.params["indisk"],
                                                                               "inseq": 1,
                                                                               "calsour": [calibrator["NAME"]],
                                                                               "timerang": [0],
                                                                               "refant": context.get_context()["ref_ant"]["ID"],
                                                                               "aparm": [2, 0, 1, 0, 0, 0, 7],
                                                                               "dparm": [0],
                                                                               "solint": -1,
                                                                               "docalib": -1,
                                                                               "identifier": f"FRING({calibrator['NAME']})"})
                task_fring.run(context)
                task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({"inname": target["NAME"],
                                                                               "inclass": "SPLAT",
                                                                               "indisk": self.params["indisk"],
                                                                               "inseq": 1,
                                                                               "calsour": [calibrator["NAME"]],
                                                                               "sources": [calibrator["NAME"]],
                                                                               "opcode": "CALP",
                                                                               "interpol": "AMBG",
                                                                               "smotyp": "VLBI",
                                                                               "bparm": [0, 0, 1, 0],
                                                                               "sn_source": f"FRING({calibrator['NAME']})",
                                                                               "cl_source": "SPLAT",
                                                                               "identifier": f"CLCAL(FRING({calibrator['NAME']}))"})
                task_clcal.run(context)
                context.logger.info(f"Calibrator {calibrator['NAME']} fringe fitting done")

        context.logger.info("Calibrator fringe fitting finished")
        return True
