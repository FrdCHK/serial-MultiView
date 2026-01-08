import os
from typing import List

from core.Plugin import Plugin
from core.Context import Context


class FitsExport(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Split and export FITS file. The classmethod export() should be used."
    
    def run(self, context: Context) -> bool:
        context.logger.debug(f"This run funtion does nothing. Please use the classmethod export() instead.")
        return True
    
    @classmethod
    def export(cls, context: Context, inname: str, inclass: str, indisk: int, inseq: int, gainuse: int, source_name: str, export_dir: str, aparm: List=[0], ident_suffix: str=" MAPPING", file_suffix: str="_FITTP") -> bool:
        try:
            identifier = f"{source_name}{ident_suffix}"
            task_split = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "SPLIT",
                                                                                "inname": inname,
                                                                                "inclass": inclass,
                                                                                "indisk": indisk,
                                                                                "inseq": inseq,
                                                                                "sources": [source_name],
                                                                                "docalib": 1,
                                                                                "gainuse": gainuse,
                                                                                "aparm": aparm,
                                                                                "outdisk": indisk})
            task_split.run(context)
            if not context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context,
                                                                                      source_name,
                                                                                      "SPLIT",
                                                                                      indisk,
                                                                                      identifier,
                                                                                      history="Created by SPLIT"):
                return False
            context.logger.debug(f"Source {source_name} SPLIT done")

            params_fittp = {"in_cat_ident": identifier}
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_fittp)
            fits_dir = os.path.join(export_dir, f"{source_name}{file_suffix}.fits")
            task_fittp = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "FITTP",
                                                                                 "inname": source_name,
                                                                                 "inclass": "SPLIT",
                                                                                 "indisk": indisk,
                                                                                 "inseq": params_fittp["inseq"],
                                                                                 "dataout": fits_dir})
            task_fittp.run(context)
            context.logger.debug(f"Source {source_name} FITTP done")
        except Exception as e:
            context.logger.error(f"Error in FitsExport.export(): {e}")
            return False
        else:
            context.logger.info(f"Source {source_name} FITS exported")
            return True
