import os

from core.Context import Context

def unzip(context: Context, file_path: str) -> bool:
    try:
        os.system(f'gunzip {file_path}')
    except Exception as e:
        context.logger.error(f"File unzip failed, original error info: {e}")
        return False
    else:
        context.logger.debug(f"File unzipped")
        return True
