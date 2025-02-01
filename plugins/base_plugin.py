# plugins/base_plugin.py
from abc import ABC, abstractmethod

class BasePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the plugin."""
        pass

    @property
    def data_format(self) -> str:
        """Data return format."""
        return "json"  # Default data format

    @property
    def required_api_keys(self) -> list:
        """List of required API key names for the plugin."""
        return []

    @abstractmethod
    def run(self, target: str) -> dict:
        """
        Execute the plugin's functionality.

        :param target: URL, IP, or domain name.
        :return: Result as a dictionary.
        """
        pass
