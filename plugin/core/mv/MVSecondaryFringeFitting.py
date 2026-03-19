"""
Secondary calibrator fringe fitting for MultiView.
@Author: Jingdong Zhang
@DATE  : 2026/03/12
"""
import os

from core.Plugin import Plugin
from core.Context import Context


class MVSecondaryFringeFitting(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Fringe fitting for secondary calibrators only. " \
               "Plugins required: AipsCatalog, Fring, Clcal, MVPrimaryFringeFitting. " \
               "Parameters required: indisk, aparm, dparm, solint, opcode, interpol, smotyp, bparm; " \
               "optional: cl_source, structure, docalib, in2class, cmethod, cmodel, cparm."

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

            use_structure = bool(self.params.get("structure", False))
            default_cl_source = f"CLCAL(FRING({primary['NAME']} STRUC))" if use_structure else f"CLCAL(FRING({primary['NAME']}))"
            cl_source = self.params.get("cl_source", default_cl_source)
            for calibrator in target["CALIBRATORS"]:
                if calibrator["NAME"] == primary["NAME"]:
                    continue
                fring_identifier = f"FRING({calibrator['NAME']} STRUC)" if use_structure else f"FRING({calibrator['NAME']})"
                clcal_identifier = f"CLCAL(FRING({calibrator['NAME']} STRUC))" if use_structure else f"CLCAL(FRING({calibrator['NAME']}))"
                task_fring_params = {
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
                    "docalib": self.params.get("docalib", 1),
                    "cl_source": cl_source,
                    "identifier": fring_identifier,
                }
                if use_structure:
                    workspace_dir = context.get_context()["config"]["workspace"]
                    struc_fits = os.path.join(workspace_dir, "targets", target["NAME"], "struc", f"{calibrator['NAME']}_selfcal.fits")
                    if not os.path.exists(struc_fits):
                        context.logger.error(f"Structure model not found: {struc_fits}")
                        return False
                    map_identifier = f"DIFMAP({calibrator['NAME']} STRUC)"
                    task_fitld = context.get_context()["loaded_plugins"]["Fitld"]({
                        "datain": struc_fits,
                        "outname": calibrator["NAME"],
                        "outclass": self.params.get("in2class", "ICLN"),
                        "out_cat_ident": map_identifier,
                    })
                    if not task_fitld.run(context):
                        return False
                    task_fring_params["in2name"] = calibrator["NAME"]
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
                    "calsour": [calibrator["NAME"]],
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
                context.logger.info(f"Secondary calibrator {calibrator['NAME']} fringe fitting done")

        context.logger.info("MV secondary calibrator fringe fitting finished")
        return True
