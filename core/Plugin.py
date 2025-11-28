import abc
from typing import Dict, Any


class Plugin(abc.ABC):
    """Abstract base class for plugins."""
    def __init__(self, params: Dict[str, Any] = {}):
        """
        initiate the plugin
        :param params: parameters for the plugin
        """
        self.params = params

    @classmethod
    def get_name(cls):
        """Get the name of the plugin."""
        return cls.__name__

    @classmethod
    def get_description(cls) -> str:
        """Get the description of the plugin."""
        return "no description provided"
    
    # @staticmethod
    # def load_priority() -> int:
    #     """Plugin load priority. The lower the number, the earlier the plugin is loaded."""
    #     return 100

    @abc.abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Run the plugin."""
