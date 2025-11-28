import logging
from typing import Dict, Type
import os
import importlib
import pkgutil
import inspect

from core.Plugin import Plugin


def plugin_load(plugin_path: str, logger: logging.Logger) -> Dict[str, Type[Plugin]]:
    logger.info("Start loading plugins")
    if os.path.isdir(plugin_path):
        try:
            package_name = plugin_path.replace(os.sep, '.')
            package = importlib.import_module(package_name)
        except Exception as e:
            logger.error(f"Cannot import package {package_name}: {e}")
            return {}
        found_plugins: Dict[str, Type[Plugin]] = {}
        for _, module_name, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            if not ispkg:
                try:
                    module = importlib.import_module(module_name)
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, Plugin) and obj is not Plugin:
                            plugin_name = obj.get_name()
                            logger.info(f"Registering {plugin_name} from {module_name}")
                            found_plugins[plugin_name] = obj
                except Exception as e:
                    logger.error(f"Could not load plugin from {module_name}: {e}")
        logger.info("Finish loading plugins")
        return found_plugins
    return {}
