import importlib
import inspect
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from python_bugreport_parser.bugreport.bugreport_all import Bugreport
from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt

logger = logging.getLogger(__name__)
plugin_dir = Path(__file__).parent


class BugreportAnalysisContext:
    def __init__(self):
        self.bugreport: Bugreport = None

        # The analysis, not only the reports strings
        self.results: List[(BasePlugin, str)] = []


class BasePlugin(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
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
    def analyze_all(cls, analysis_context: BugreportAnalysisContext) -> None:
        """Run analysis using all plugins"""
        with cls._lock:
            for plugin in cls._plugins:
                plugin.analyze(analysis_context)

    @classmethod
    def report_all(cls) -> str:
        """Generate reports from all plugins"""
        with cls._lock:
            reports = [plugin.report() for plugin in cls._plugins]
            return "\n".join(reports)

    # Registerations for plugins at the import of this module
    @classmethod
    def load_plugins(cls):
        # Scan the plugin directory
        plugin_files = Path(plugin_dir).glob("*.py")

        with cls._lock:
            for file_path in plugin_files:
                module_name = file_path.stem  # e.g., "foo" from "foo.py"
                if module_name == "__init__":
                    continue
                try:
                    # Import the module dynamically
                    module = importlib.import_module(
                        f"python_bugreport_parser.plugins.{module_name}"
                    )

                    # Find all classes in the module that inherit from BasePlugin
                    for _, plugin_cls in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(plugin_cls, BasePlugin)
                            and plugin_cls is not BasePlugin
                        ):
                            plugin_instance = plugin_cls()
                            cls._plugins.append(plugin_instance)
                            break  # Assume one plugin per file for simplicity

                except Exception as e:
                    print(f"Failed to load {module_name}: {e}")
            print(
                f"Successfully loaded the following plugins: {[plugin.name() for plugin in cls._plugins]}"
            )


PluginRepo.load_plugins()
