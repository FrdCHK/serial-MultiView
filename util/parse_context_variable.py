from core.Context import Context

def parse_context_variable(obj, context: Context, strict=True, default=None):
    """
    Recursively substitute $a:b:c$ strings using values from context.
    """

    if isinstance(obj, dict):
        return {
            key: parse_context_variable(value, context, strict=strict, default=default)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [
            parse_context_variable(item, context, strict=strict, default=default)
            for item in obj
        ]
    elif isinstance(obj, tuple):
        return tuple(
            parse_context_variable(item, context, strict=strict, default=default)
            for item in obj
        )
    elif isinstance(obj, str):
        if obj.startswith("$") and obj.endswith("$"):
            path = obj[1:-1].split(":")
            return resolve_context_path(context, path, strict=strict, default=default)
        return obj
    else:
        return obj

def resolve_context_path(context: Context, path: list, strict=True, default=None):
    """
    Resolve a list of keys against a nested context dict.

    Parameters
    ----------
    context : dict
        The context dictionary.
    path : list[str]
        Hierarchical keys, e.g. ["a", "b", "c"].
    strict : bool
        If True, raise KeyError on missing path.
        If False, return default.
    default : any
        Returned when strict=False and path is invalid.
    """
    current = context.get_context()
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            if strict:
                raise KeyError(f"Context path not found: {'/'.join(path)}")
            return default
    return current
