# utils/plugin_loader.py
import os
import importlib
from plugins.base_plugin import BasePlugin

def load_plugins(plugin_folder: str, logger=None):
    plugins = []
    if not os.path.exists(plugin_folder):
        if logger:
            logger.error(f"Plugin folder '{plugin_folder}' does not exist.")
        return plugins

    for filename in os.listdir(plugin_folder):
        if filename.endswith(".py") and filename != "base_plugin.py":
            module_name = filename[:-3]
            module_path = f"plugins.{module_name}"
            try:
                module = importlib.import_module(module_path)
                for attribute in dir(module):
                    attribute_obj = getattr(module, attribute)
                    if isinstance(attribute_obj, type) and issubclass(attribute_obj, BasePlugin) and attribute_obj != BasePlugin:
                        plugin_instance = attribute_obj()
                        plugins.append(plugin_instance)
                        if logger:
                            logger.info(f"Loaded plugin: {plugin_instance.name}")
            except Exception as e:
                if logger:
                    logger.error(f"Failed to load plugin '{module_name}': {str(e)}")
    return plugins
