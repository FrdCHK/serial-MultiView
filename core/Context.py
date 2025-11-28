import yaml
import logging
from typing import Dict, Any


class Context:
    def __init__(self, logger: logging.Logger, path: str):
        logger.info("Start initiating context")
        self.path = path
        self.logger = logger
        self.context = self.init_context_from_config()

    def init_context_from_config(self):
        try:
            with open(self.path, 'r') as f:
                self.logger.info(f"Configuration file {self.path} loaded successfully")
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load configuration file {self.path}: {e}")
            return {}

    def get_context(self):
        return self.context
    
    def edit_context(self, context: Dict[str, Any]):
        for item in context:
            self.context[item] = context[item]
