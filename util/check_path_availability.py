from typing import Tuple
import os

def check_path_availability(path: str) -> Tuple[bool, str]:
    if os.path.exists(path):
        if os.path.isfile(path):
            return True, 'file'
        elif os.path.isdir(path):
            return True, 'dir'
    return False, 'none'
