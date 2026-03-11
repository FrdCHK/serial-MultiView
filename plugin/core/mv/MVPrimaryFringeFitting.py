from core.Plugin import Plugin
from core.Context import Context


class MVPrimaryFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fit primary calibrator and apply to all sources in each target SPLAT. " \
               "Plugins required: AipsCatalog, Fring, Clcal, MVPrimaryCalibratorSelect. " \
               "Parameters required: indisk, aparm, dparm, solint, opcode, interpol, smotyp, bparm."

    def run(self, context: Context) -> bool:
        context.logger.info("Start primary calibrator fringe fitting")

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

            task_fring = context.get_context()["loaded_plugins"]["Fring"]({
                "inname": target["NAME"],
                "inclass": "SPLAT",
                "indisk": self.params["indisk"],
                "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                "calsour": [primary["NAME"]],
                "timerang": [0],
                "refant": context.get_context()["ref_ant"]["ID"],
                "aparm": self.params["aparm"],
                "dparm": self.params["dparm"],
                "solint": self.params["solint"],
                "docalib": -1,
                "identifier": f"FRING({primary['NAME']})",
            })
            task_fring.run(context)

            task_clcal = context.get_context()["loaded_plugins"]["Clcal"]({
                "inname": target["NAME"],
                "inclass": "SPLAT",
                "indisk": self.params["indisk"],
                "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS",
                "calsour": [primary["NAME"]],
                "sources": [target["NAME"]] + [c["NAME"] for c in target.get("CALIBRATORS", [])],
                "opcode": self.params["opcode"],
                "interpol": self.params["interpol"],
                "smotyp": self.params["smotyp"],
                "bparm": self.params["bparm"],
                "sn_source": f"FRING({primary['NAME']})",
                "cl_source": "SPLAT",
                "identifier": f"CLCAL(FRING({primary['NAME']}))",
            })
            task_clcal.run(context)
            context.logger.info(f"Primary calibrator {primary['NAME']} fringe fitting done for {target['NAME']}")

        context.logger.info("Primary calibrator fringe fitting finished")
        return True
