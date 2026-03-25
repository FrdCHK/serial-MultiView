"""
Export SN tables for MultiView.
@Author: Jingdong Zhang
@DATE  : 2026/03/12
"""
import os
import math
import yaml
import pandas as pd
from typing import Dict, Any
from AIPSData import AIPSUVData

from core.Plugin import Plugin
from core.Context import Context


class MVSnExport(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Export SN tables of secondary calibrators to CSV for MultiView. " \
               "Plugins required: AipsCatalog, PRCalibratorFringeFitting. " \
               "Parameters required: indisk."

    def run(self, context: Context) -> bool:
        context.logger.info("Start MultiView SN export")

        if not context.get_context().get("targets", []):
            context.logger.error("No targets found in the context")
            return False

        workspace_dir = context.get_context()["config"]["workspace"]
        indisk = int(self.params["indisk"])

        for target in context.get_context().get("targets"):
            primary = target.get("primary_calibrator") or target.get("PRIMARY_CALIBRATOR")
            if primary is None:
                context.logger.error(f"Primary calibrator not found for target {target['NAME']}")
                return False
            if isinstance(primary, list):
                primary = primary[0]
            primary_id = int(primary["ID"])

            target_dir = os.path.join(workspace_dir, "targets", target["NAME"])
            mv_dir = os.path.join(target_dir, "mv")
            sn_dir = os.path.join(mv_dir, "SN")
            os.makedirs(sn_dir, exist_ok=True)

            params_target: Dict[str, Any] = {"in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
            if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target):
                params_target = {"in_cat_ident": f"{target['NAME']}"}
                if not context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target):
                    context.logger.error(f"Target SPLAT catalog not found for {target['NAME']}")
                    return False

            splat_uv = AIPSUVData(target["NAME"], "SPLAT", indisk, int(params_target["inseq"]))
            calibrators = target.get("CALIBRATORS", [])
            for calibrator in calibrators:
                if int(calibrator["ID"]) == primary_id:
                    continue
                sn_sources = [f"FRING({calibrator['NAME']} STRUC)", f"FRING({calibrator['NAME']})"]
                ext = {"status": False}
                sn_source = ""
                for source in sn_sources:
                    ext = context.get_context()["loaded_plugins"]["AipsCatalog"].search_ext(
                        context,
                        target["NAME"],
                        "SPLAT",
                        indisk,
                        int(params_target["inseq"]),
                        "SN",
                        ext_source=source,
                    )
                    if ext["status"]:
                        sn_source = source
                        break
                if not ext["status"]:
                    context.logger.error(f"SN table not found for calibrator {calibrator['NAME']} on target {target['NAME']}")
                    return False
                snver = context.get_context()["aips_catalog"][ext["cat_index"]]["ext"][ext["ext_index"]]["version"][ext["ver_index"]]["num"]
                calibrator["SN"] = int(snver)

                sn_table = splat_uv.table("SN", int(snver))
                phase_column = [f"p{if_id}" for if_id in range(context.get_context()["no_if"])]
                delay_column = [f"d{if_id}" for if_id in range(context.get_context()["no_if"])]
                rate_column = [f"r{if_id}" for if_id in range(context.get_context()["no_if"])]
                sn_df = pd.DataFrame(columns=["t", "antenna", "calsour", "mbdelay"] + phase_column + delay_column + rate_column)
                for row_sn in sn_table:
                    no_if = context.get_context()["no_if"]
                    phase = [math.atan2(row_sn.imag1[if_id], row_sn.real1[if_id]) for if_id in range(no_if)]
                    delay = [row_sn.delay_1[if_id] for if_id in range(no_if)]
                    rate = [row_sn.rate_1[if_id] for if_id in range(no_if)]
                    mbdelay = row_sn.mbdelay1
                    sn_df.loc[sn_df.index.size] = [row_sn.time, row_sn.antenna_no, row_sn.source_id, mbdelay] + phase + delay + rate
                sn_path = os.path.join(sn_dir, f"{target['ID']}-{target['NAME']}-SN{snver}.csv")
                sn_df.to_csv(sn_path, index=False)
                context.logger.info(f"SN{snver}({sn_source}) for {target['NAME']} exported")

            target_conf = {
                "PRIMARY_CALIBRATOR": primary,
                "CALIBRATORS": calibrators,
                "MV_FLAG": False,
            }
            target_conf_path = os.path.join(mv_dir, f"{target['ID']}-{target['NAME']}.yaml")
            with open(target_conf_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(target_conf, f)

        context.logger.info("MultiView SN export finished")
        return True
