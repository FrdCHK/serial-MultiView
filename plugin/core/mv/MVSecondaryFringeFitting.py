from core.Plugin import Plugin
from core.Context import Context


class MVSecondaryFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fitting for secondary calibrators only. " \
               "Plugins required: AipsCatalog, Fring, Clcal, MVPrimaryFringeFitting. " \
               "Parameters required: indisk, aparm, dparm, solint, opcode, interpol, smotyp, bparm; " \
               "optional: cl_source."

    def run(self, context: Context) -> bool:
        context.logger.info("Start MV secondary calibrator fringe fitting")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False

        for target in context.get_context().get("targets"):
            primary = target.get("primary_calibrator") or target.get("PRIMARY_CALIBRATOR")
            if primary is None:
                context.logger.error(f"Primary calibrator not found for target {target['NAME']}")
                return False
            if isinstance(primary, list):
                primary = primary[0]

            cl_source = self.params.get("cl_source", f"CLCAL(FRING({primary['NAME']}))")
            for calibrator in target["CALIBRATORS"]:
                if calibrator["NAME"] == primary["NAME"]:
                    continue
                task_fring = context.get_context()["loaded_plugins"]["Fring"]({
                    "inname": target["NAME"],
                    "inclass": "SPLAT",
                    "indisk": self.params["indisk"],
                    "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                    "calsour": [calibrator["NAME"]],
                    "timerang": [0],
                    "refant": context.get_context()["ref_ant"]["ID"],
                    "aparm": self.params["aparm"],
                    "dparm": self.params["dparm"],
                    "solint": self.params["solint"],
                    "docalib": 1,
                    "cl_source": cl_source,
                    "identifier": f"FRING({calibrator['NAME']})",
                })
                task_fring.run(context)
                task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({
                    "inname": target["NAME"],
                    "inclass": "SPLAT",
                    "indisk": self.params["indisk"],
                    "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                    "calsour": [calibrator["NAME"]],
                    "opcode": self.params["opcode"],
                    "interpol": self.params["interpol"],
                    "smotyp": self.params["smotyp"],
                    "bparm": self.params["bparm"],
                    "sn_source": f"FRING({calibrator['NAME']})",
                    "cl_source": cl_source,
                    "identifier": f"CLCAL(FRING({calibrator['NAME']}))",
                })
                task_clcal.run(context)
                context.logger.info(f"Secondary calibrator {calibrator['NAME']} fringe fitting done")

        context.logger.info("MV secondary calibrator fringe fitting finished")
        return True
