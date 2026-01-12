from typing import Any
import yaml

from core.Plugin import Plugin
from core.Context import Context


class SourceSelect(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Abstract class for source selection. Do not try to instantiate this class." \
        "Plugins required: AipsCatalog, GeneralTask."
    
    def predef_load(self, context: Context) -> int:
        if "in_cat_ident" in self.params:
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, self.params)
        
        if self.params.get("load", None):
            # load sources from file (context of another experiment)
            try:
                with open(self.params["load"], 'r') as f:
                    predef = yaml.safe_load(f)
            except Exception as e:
                context.logger.warning(f"Failed to load predef source list file {self.params['load']}: {e}")
                context.logger.info(f"Continue with manual selection")
            else:
                predef_targets = predef.get("targets", [])
                if predef_targets:
                    # replace IDs in predef list with the actual IDs of these sources in the current experiment
                    self.replace_source_id(predef_targets, context)
                    context.edit_context({"targets": predef_targets})
                    context.logger.info(f"Predef source list file {self.params['load']} loaded successfully")
                    if not self.splat(context):
                        return -1
                    return 0
                else:
                    context.logger.warning(f"Predef source list file {self.params['load']} does not contain targets")
                    context.logger.info(f"Continue with manual selection")
                    return 1
            # if encounter error, just catch and log it and continue with manual selection
        else:
            return 1

    def splat(self, context: Context, identifier_suffix: str=" WITH CALIBRATORS") -> bool:
        if not context.get_context()["loaded_plugins"]["AipsCatalog"].source2ver(context, self.params, "CL", "gainuse"):
            context.logger.error(f"CL source not found in context")
            return False
        for target in context.get_context()["targets"]:
            if "CALIBRATORS" in target:
                sources = [target["NAME"], *[calibrator["NAME"] for calibrator in target["CALIBRATORS"]]]
            else:
                sources = [target["NAME"]]
                if identifier_suffix == " WITH CALIBRATORS":
                    identifier_suffix = ""
            task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "SPLAT",
                                                                           "inname": self.params["inname"],
                                                                           "inclass": self.params["inclass"],
                                                                           "indisk": self.params["indisk"],
                                                                           "inseq": self.params["inseq"],
                                                                           "sources": sources,
                                                                           "docalib": 1,
                                                                           "gainuse": self.params["gainuse"],
                                                                           "outname": target["NAME"],
                                                                           "outdisk": self.params["indisk"]})
            task.run(context)
            if not context.get_context()["loaded_plugins"]["AipsCatalog"].add_catalog(context,
                                                                                      target["NAME"],
                                                                                      "SPLAT",
                                                                                      self.params["indisk"],
                                                                                      f"{target['NAME']}{identifier_suffix}",
                                                                                      history="Created by SPLAT"):
                return False
        return True

    @classmethod
    def replace_source_id(cls, obj, context: Context) -> Any:
        if isinstance(obj, dict):
            if ("ID" in obj) and ("NAME" in obj):
                for source in context.get_context()["sources"]:
                    if source["NAME"] == obj["NAME"]:
                        obj["ID"] = source["ID"]
                        break
            return {
                key: cls.replace_source_id(value, context)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                cls.replace_source_id(item, context)
                for item in obj
            ]
        else:
            return obj
