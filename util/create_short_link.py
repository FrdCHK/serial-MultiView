import os
import tempfile
from typing import Tuple


def create_short_link(target: str, dir: str="/tmp", prefix: str="", suffix: str="") -> Tuple[str, str]:
    target_parent_dir = os.path.dirname(os.path.abspath(target))
    with tempfile.NamedTemporaryFile(dir=dir, prefix=prefix, suffix=suffix, delete=False) as f:
        link_path = f.name
    # Replace the temp file with a symlink
    os.remove(link_path)
    os.symlink(target_parent_dir, link_path)
    return link_path, os.path.join(link_path, os.path.basename(target))
