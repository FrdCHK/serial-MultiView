import os

def check_path_availability(path: str) -> str:
    if os.path.exists(path):
        if os.path.isfile(path):
            return 'file'
        elif os.path.isdir(path):
            return 'dir'
    return 'none'
