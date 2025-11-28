import os
import logging
from datetime import datetime


def logger_init(directory: str) -> logging.Logger:
    # initiate logger
    log_filename = datetime.now().strftime("log_%Y%m%d_%H%M%S.log")
    logger = logging.getLogger(log_filename)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    os.makedirs(directory, exist_ok=True)
    log_file_path = os.path.join(directory, log_filename)
    file_handler = logging.FileHandler(log_file_path)
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
