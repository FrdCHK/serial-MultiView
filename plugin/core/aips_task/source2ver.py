from typing import Dict, Any

from core.Context import Context


def source2ver(context: Context, params: Dict[str, Any], ext_type: str) -> bool:
    """
    Search for extension version based on extension source. The version number is directly added to params.
    
    :param context: context instance
    :type context: Context
    :param params: parameters
    :type params: Dict[str, Any]
    :param ext_type: extension type. SN or CL
    :type ext_type: str
    :return: whether the search is successful
    :rtype: bool
    """
    if ext_type == "SN":
        ext_source_key = "sn_source"
        new_param_key = "snver"
    elif ext_type == "CL":
        ext_source_key = "cl_source"
        new_param_key = "gainver"
    else:
        return False
    ext_search_result = context.get_context()["loaded_plugins"]["AipsCatalog"].search_ext(context,
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
