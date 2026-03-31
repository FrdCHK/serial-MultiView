"""
YAML helpers.
@Author: OpenAI Codex
@DATE  : 2026/4/1
"""
import yaml
import numpy as np


def to_builtin(value):
    """
    Recursively convert numpy scalars/arrays into plain Python objects so YAML
    serialization is stable.
    """
    if isinstance(value, dict):
        return {to_builtin(key): to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    if isinstance(value, np.ndarray):
        return [to_builtin(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    return value


def safe_dump_builtin(data, stream, **kwargs):
    yaml.safe_dump(to_builtin(data), stream, **kwargs)
