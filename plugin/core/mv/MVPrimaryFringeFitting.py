"""
Primary calibrator fringe fitting for MultiView.
@Author: Jingdong Zhang
@DATE  : 2026/03/12
"""
import os

from core.Plugin import Plugin
from core.Context import Context


class MVPrimaryFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fit primary calibrator and apply to all sources in each target SPLAT. " \
               "Plugins required: AipsCatalog, Fring, Clcal, MVPrimaryCalibratorSelect. " \
               "Parameters required: indisk, aparm, dparm, solint, opcode, interpol, smotyp, bparm; " \
               "optional: structure, cl_source, docalib, in2class, cmethod, cmodel, cparm."

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
            use_structure = bool(self.params.get("structure", False))
            cl_source = self.params.get("cl_source", "SPLAT")

            fring_identifier = f"FRING({primary['NAME']} STRUC)" if use_structure else f"FRING({primary['NAME']})"
            clcal_identifier = f"CLCAL(FRING({primary['NAME']} STRUC))" if use_structure else f"CLCAL(FRING({primary['NAME']}))"
            task_fring_params = {
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
                "docalib": self.params.get("docalib", -1),
                "cl_source": cl_source,
                "identifier": fring_identifier,
            }

            if use_structure:
                workspace_dir = context.get_context()["config"]["workspace"]
                struc_fits = os.path.join(workspace_dir, "targets", target["NAME"], "struc", f"{primary['NAME']}_selfcal.fits")
                if not os.path.exists(struc_fits):
                    context.logger.error(f"Structure model not found: {struc_fits}")
                    return False
                map_identifier = f"DIFMAP({primary['NAME']} STRUC)"
                task_fitld = context.get_context()["loaded_plugins"]["Fitld"]({
                    "datain": struc_fits,
                    "outname": primary["NAME"],
                    "outclass": self.params.get("in2class", "ICLN"),
                    "out_cat_ident": map_identifier,
                })
                if not task_fitld.run(context):
                    return False
                task_fring_params["in2name"] = primary["NAME"]
                task_fring_params["in2class"] = self.params.get("in2class", "ICLN")
                task_fring_params["in2disk"] = self.params["indisk"]
                task_fring_params["in2_cat_ident"] = map_identifier
                if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, task_fring_params, "in2_cat_ident", "in2seq"):
                    return False
                task_fring_params["cmethod"] = self.params.get("cmethod", "DFT")
                task_fring_params["cmodel"] = self.params.get("cmodel", "COMP")
                task_fring_params["cparm"] = self.params.get("cparm", [0, 1])

            task_fring = context.get_context()["loaded_plugins"]["Fring"](task_fring_params)
            if not task_fring.run(context):
                return False

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
                "sn_source": fring_identifier,
                "cl_source": cl_source,
                "identifier": clcal_identifier,
            })
            if not task_clcal.run(context):
                return False
            context.logger.info(f"Primary calibrator {primary['NAME']} fringe fitting done for {target['NAME']}")

        context.logger.info("Primary calibrator fringe fitting finished")
        return True
