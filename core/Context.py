import yaml
import logging
import os
from typing import Dict, Any


class Context:
    def __init__(self, logger: logging.Logger, control_file_path: str):
        """
        Init context from control file (and context file, optional)
        
        :param logger: logger instance
        :type logger: logging.Logger
        :param control_file_path: Path to control file
        :type control_file_path: str
        """
        logger.info("Start initiating context")
        self.control_file_path = control_file_path
        self.logger = logger
        self.context = self.init_context_from_control()
        self.edit_context({"logger": logger})
        self.edit_context({"control_file_path": control_file_path})
        self.context_file_path = os.path.join(self.context["config"]["workspace"], "context.yaml")
        self.edit_context({"context_file_path": self.context_file_path})
        self.edit_context(self.load_context_from_file())
        self.edit_context(self.init_context_from_control())  # load from control file again to override cached context

    def init_context_from_control(self):
        try:
            with open(self.control_file_path, 'r') as f:
                self.logger.info(f"Control file {self.control_file_path} loaded successfully")
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load control file {self.control_file_path}: {e}")
            return {}

    def get_context(self):
        return self.context
    
    def edit_context(self, context: Dict[str, Any]):
        if context:
            for item in context:
                self.context[item] = context[item]

    def load_context_from_file(self):
        try:
            with open(self.context_file_path, 'r') as f:
                self.logger.info(f"Context file {self.context_file_path} loaded successfully")
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.info(f"Context file {self.context_file_path} not available")
            return {}
    
    @classmethod
    def filter_basic_structure(cls, obj: Dict, allowed_types=(int, float, bool, str, type(None))) -> Dict:
        if isinstance(obj, allowed_types):
            return obj
        elif isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                filtered_v = cls.filter_basic_structure(v)
                if filtered_v is not None:
                    result[k] = filtered_v
            return result
        elif isinstance(obj, (list, tuple)):
            filtered = [
                cls.filter_basic_structure(v)
                for v in obj
            ]
            filtered = [v for v in filtered if v is not None]
            return type(obj)(filtered)
        else:
            return None

    def save_context_to_file(self):
        try:
            with open(self.context_file_path, 'w') as f:
                yaml.safe_dump(self.filter_basic_structure(self.context), f)
                self.logger.info(f"Context saved to {self.context_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save context to {self.context_file_path}: {e}")
