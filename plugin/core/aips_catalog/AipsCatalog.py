# import yaml
# import os
from typing import Dict, Any, Union

from core.Plugin import Plugin
from core.Context import Context
# from util.check_path_availability import check_path_availability


class AipsCatalog(Plugin):
    def __init__(self, params: Dict[str, Any] = {"catalog_file": "aips_catalog.yaml"}):
        """
        initiate the plugin
        :param params: parameters for the plugin
        """
        self.params = params

    @classmethod
    def get_description(cls) -> str:
        return "manage AIPS catalog and extension file information"

    def run(self, context: Context) -> bool:
        """This run method is only for context init"""
        context.logger.info("Start AIPS catalog and extension file information init")
        # workspace_path = context.get_context()["config"]["workspace"]
        # if not workspace_path:
        #     context.logger.error("Workspace not defined")
        #     return False
        # else:
        #     catalog_path = os.path.join(workspace_path, "aips_catalog.yaml")
        #     if check_path_availability(catalog_path) == 'file':
        #         with open(catalog_path, "r") as f:
        #             catalog = yaml.safe_load(f)
        #         if catalog is None:
        #             catalog = []
        #         context.edit_context({"aips_catalog": catalog})
        #     else:
        #         context.edit_context({"aips_catalog": []})
        if context.get_context().get("aips_catalog") is None:
            context.edit_context({"aips_catalog": []})
        return True

    # @classmethod
    # def save_catalog(cls, context: Context) -> bool:
    #     catalog_path = os.path.join(context.get_context()["config"]["workspace"], "aips_catalog.yaml")
    #     with open(catalog_path, "w") as f:
    #         yaml.safe_dump(context.get_context().get("aips_catalog", []), f)
    #     context.logger.info(f"AIPS catalog saved to {catalog_path}")
    #     return True

    @classmethod
    def search_catalog(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int) -> int:
        catalog = context.get_context().get("aips_catalog", [])
        if catalog:
            for index, item in enumerate(catalog):
                if item["name"] == cat_name and item["class"] == cat_class and item["disk"] == cat_disk and item["seq"] == cat_seq:
                    context.logger.debug(f"Catalog found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
                    return index
        context.logger.debug(f"Catalog not found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        return -1

    @classmethod
    def get_highest_catalog_seq(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int) -> int:
        highst_seq = 0
        for item in context.get_context().get("aips_catalog", []):
            if item["name"] == cat_name and item["class"] == cat_class and item["disk"] == cat_disk:
                highst_seq = max(highst_seq, item["seq"])
        return highst_seq

    @classmethod
    def add_catalog(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int=0, history: str="Created") -> bool:
        if cat_seq > 0 and cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq) >= 0:
            context.logger.error(f"Catalog already exists: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        if cat_seq == 0:
            cat_seq = cls.get_highest_catalog_seq(context, cat_name, cat_class, cat_disk) + 1
        context.get_context()["aips_catalog"].append({"name": cat_name, "class": cat_class, "disk": cat_disk, "seq": cat_seq, "ext": [], "history": [history]})
        # if uv data, add CL1 to its ext list
        if cat_class == "UVDATA":
            context.get_context()["aips_catalog"][-1]["ext"].append({"type": "CL", "version": [{"num": 1, "source": "FITLD"}]})
        elif cat_class == "SPLAT":
            context.get_context()["aips_catalog"][-1]["ext"].append({"type": "CL", "version": [{"num": 1, "source": "SPLAT"}]})
        elif cat_class == "SPLIT":
            context.get_context()["aips_catalog"][-1]["ext"].append({"type": "CL", "version": [{"num": 1, "source": "SPLIT"}]})
        context.logger.debug(f"Catalog added: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        return True

    @classmethod
    def del_catalog(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int=0) -> bool:
        if cat_seq == 0:
            cat_seq = cls.get_highest_catalog_seq(context, cat_name, cat_class, cat_disk)
        cat_index = cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq)
        if cat_index < 0:
            context.logger.error(f"Catalog not found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        context.get_context()["aips_catalog"].pop(cat_index)
        context.logger.debug(f"Catalog deleted: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        return True

    @classmethod
    def append_history(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int, history: str) -> bool:
        cat_index = cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq)
        if cat_index < 0:
            context.logger.error(f"Catalog not found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        context.get_context()["aips_catalog"][cat_index]["history"].append(history)
        return True

    @classmethod
    def search_ext(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int, ext_type: str, ext_version: int=0, ext_source: str="") -> Dict[str, Union[bool, int]]:
        """Search with ext type+version or type+source. If both are specified, search with type+version. Returns a dict with keys: status (bool), ext_index (int), and ver_index (int)."""
        if ext_version > 0:
            logger_text = f"{ext_type}{ext_version}"
        elif ext_source != "":
            logger_text = f"{ext_type}({ext_source})"
        else:
            context.logger.error("Ext version or source must be specified")
            return {"status": False, "cat_index": -1, "ext_index": -1, "ver_index": -1}
        
        cat_index = cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq)
        if cat_index < 0:
            context.logger.error(f"Catalog not found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return {"status": False, "cat_index": -2, "ext_index": -2, "ver_index": -2}
        
        for ext_index, item in enumerate(context.get_context()["aips_catalog"][cat_index]["ext"]):
            if item["type"] == ext_type:
                if ext_version > 0:
                    for ver_index, ver in enumerate(item["version"]):
                        if ver["num"] == ext_version:
                            context.logger.debug(f"Ext {logger_text} found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
                            return {"status": True, "cat_index": cat_index, "ext_index": ext_index, "ver_index": ver_index}
                else:
                    for ver_index, ver in enumerate(item["version"]):
                        if ver["source"] == ext_source:
                            context.logger.debug(f"Ext {logger_text} found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
                            return {"status": True, "cat_index": cat_index, "ext_index": ext_index, "ver_index": ver_index}
        context.logger.debug(f"Ext {logger_text} not found in catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        return {"status": False, "cat_index": -3, "ext_index": -3, "ver_index": -3}
 
    @classmethod
    def get_highest_ext_ver(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int, ext_type: str) -> int:
        # Note: whether the catalog exists is NOT checked here, so make sure the catalog exists before calling this function
        # It is also possible to call AIPSUVData.table_highver('AIPS XX') to get the highest version number of a given ext type in the AIPS catalog
        cat_index = cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq)
        highst_ver = 0
        for item in context.get_context()["aips_catalog"][cat_index].get("ext", []):
            if item["type"] == ext_type:
                return max([ver["num"] for ver in item["version"]])
        context.logger.debug(f"Ext {ext_type} not found in catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        return highst_ver

    @classmethod
    def add_ext(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int, ext_type: str, ext_version: int=0, ext_source: str="DEFAULT") -> bool:
        cat_index = cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq)
        if cat_index < 0:
            context.logger.error(f"Catalog not found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        
        if ext_version > 0 and cls.search_ext(context, cat_name, cat_class, cat_disk, cat_seq, ext_type, ext_version)["status"]:
            context.logger.error(f"Ext {ext_type}{ext_version} already exists in catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        
        # whether this ext type exists in catalog (check whether version 1 exists)
        ext_search_result = cls.search_ext(context, cat_name, cat_class, cat_disk, cat_seq, ext_type, 1)
        if ext_version == 0:
            ext_version = cls.get_highest_ext_ver(context, cat_name, cat_class, cat_disk, cat_seq, ext_type) + 1
        if ext_search_result["status"]:
            # append a version to ext
            context.get_context()["aips_catalog"][cat_index]["ext"][ext_search_result["ext_index"]]["version"].append({"num": ext_version, "source": ext_source})
        else:
            # append a new ext
            context.get_context()["aips_catalog"][cat_index]["ext"].append({"type": ext_type, "version": [{"num": ext_version, "source": ext_source}]})
        context.logger.debug(f"Ext {ext_type}{ext_version}({ext_source}) added to catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        cls.append_history(context, cat_name, cat_class, cat_disk, cat_seq, f"Added ext {ext_type}{ext_version} ({ext_source})")
        return True

    @classmethod
    def del_ext(cls, context: Context, cat_name: str, cat_class: str, cat_disk: int, cat_seq: int, ext_type: str, ext_version: int=0, del_reason: str="") -> bool:
        cat_index = cls.search_catalog(context, cat_name, cat_class, cat_disk, cat_seq)
        if cat_index < 0:
            context.logger.error(f"Catalog not found: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        
        if ext_version > 0 and (not cls.search_ext(context, cat_name, cat_class, cat_disk, cat_seq, ext_type, ext_version)["status"]):
            context.logger.error(f"Ext {ext_type}{ext_version} does not exist in catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False
        if ext_version == 0 and (not cls.search_ext(context, cat_name, cat_class, cat_disk, cat_seq, ext_type, 1)["status"]):
            context.logger.error(f"Ext {ext_type} does not exist in catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
            return False

        if ext_version == 0:
            ext_version = cls.get_highest_ext_ver(context, cat_name, cat_class, cat_disk, cat_seq, ext_type)
        ext_search_result = cls.search_ext(context, cat_name, cat_class, cat_disk, cat_seq, ext_type, ext_version)

        if ext_version == 1:
            if ext_type == "CL":
                context.logger.error(f"CL1 cannot be deleted")
                return False
            # delete ext
            context.get_context()["aips_catalog"][cat_index]["ext"].pop(ext_search_result["ext_index"])
        else:
            # delete version
            context.get_context()["aips_catalog"][cat_index]["ext"][ext_search_result["ext_index"]]["version"].pop(ext_search_result["ver_index"])
        context.logger.debug(f"Ext {ext_type}{ext_version} deleted from catalog: name={cat_name} class={cat_class} disk={cat_disk} seq={cat_seq}")
        if del_reason != "":
            del_reason = f" ({del_reason})"
        cls.append_history(context, cat_name, cat_class, cat_disk, cat_seq, f"Deleted ext {ext_type}{ext_version}{del_reason}")
        return True
    
    @classmethod
    def source2ver(cls, context: Context, params: Dict[str, Any], ext_type: str, new_cl_key: str="gainver") -> bool:
        """
        Search for extension version based on extension source, and directly add to params. The version number is directly added to params.
        
        :param context: context instance
        :type context: Context
        :param params: parameters
        :type params: Dict[str, Any]
        :param ext_type: extension type. SN or CL
        :type ext_type: str
        :param new_cl_key: CL table key, 'gainver' or 'gainuse'. Defaults to 'gainver'.
        :type new_cl_key: str
        :return: whether the search is successful
        :rtype: bool
        """
        if ext_type == "SN":
            ext_source_key = "sn_source"
            new_param_key = "snver"
        elif ext_type == "CL":
            ext_source_key = "cl_source"
            new_param_key = new_cl_key
        else:
            return False
        ext_search_result = cls.search_ext(context,
                                           params["inname"],
                                           params["inclass"],
                                           params["indisk"],
                                           params["inseq"],
                                           ext_type,
                                           ext_source=params[ext_source_key])
        if not ext_search_result["status"]:
            return False
        params[new_param_key] = context.get_context()["aips_catalog"][ext_search_result["cat_index"]]["ext"][ext_search_result["ext_index"]]["version"][ext_search_result["ver_index"]]["num"]
        params.pop(ext_source_key)
        return True
