from abc import ABC, abstractmethod
import logging
from importlib.metadata import entry_points
import threading
from typing import List, Optional

from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt

logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def analyze(self, bugreport: BugreportTxt) -> None:
        pass

    @abstractmethod
    def report(self) -> str:
        pass


class PluginRepo:
    _plugins: List[BasePlugin] = []
    _lock = threading.Lock()

    @classmethod
    def register(cls, plugin: BasePlugin) -> None:
        """Register a new plugin"""
        with cls._lock:
            cls._plugins.append(plugin)

    @classmethod
    def get_all(cls) -> List[BasePlugin]:
        """Get all registered plugins"""
        with cls._lock:
            return cls._plugins.copy()

    @classmethod
    def find_by_name(cls, name: str) -> Optional[BasePlugin]:
        """Find a plugin by name"""
        with cls._lock:
            for plugin in cls._plugins:
                if plugin.name() == name:
                    return plugin
            return None

    @classmethod
    def analyze_all(cls, bugreport: "BugreportTxt") -> None:
        """Run analysis using all plugins"""
        with cls._lock:
            for plugin in cls._plugins:
                plugin.analyze(bugreport)

    @classmethod
    def report_all(cls) -> str:
        """Generate reports from all plugins"""
        with cls._lock:
            reports = [plugin.report() for plugin in cls._plugins]
            return "\n".join(reports)


# Registerations for plugins at the import of this module
