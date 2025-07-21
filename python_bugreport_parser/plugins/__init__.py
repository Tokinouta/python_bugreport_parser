import importlib
import inspect
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from python_bugreport_parser.bugreport.bugreport_all import Bugreport, Log284
from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt

logger = logging.getLogger(__name__)
plugin_dir = Path(__file__).parent


class PluginResult:
    def __init__(
        self, data: Any, result_type: str = None, metadata: Dict[str, Any] = None
    ):
        """
        A unified result container for plugin outputs.
        :param data: The actual result produced by the plugin.
        :param result_type: A string representing the type of data.
        :param metadata: Optional additional information.
        """
        self.data = data
        self.result_type = result_type
        self.metadata = metadata or {}

    def __repr__(self):
        return f"PluginResult(data={self.data}, type={self.result_type})"


class BugreportAnalysisContext:
    def __init__(self):
        self.bugreport: Log284 = None

        # The analysis, not only the reports strings
        self.results: Dict[PluginResult] = {}

    def set_result(self, plugin_name: str, result: PluginResult):
        self.results[plugin_name] = result

    def get_result(self, plugin_name: str) -> PluginResult:
        return self.results.get(plugin_name)

    def __repr__(self):
        return f"PluginContext(results={self.results})"


class BasePlugin(ABC):
    def __init__(self, name: str, dependencies: List[str] = None):
        """
        Base class for plugins.
        :param name: Unique identifier for the plugin.
        :param dependencies: List of plugin names that this plugin depends on.
        """
        self.name = name
        self.dependencies = dependencies if dependencies is not None else []

    @abstractmethod
    def analyze(self, analysis_context: BugreportAnalysisContext) -> PluginResult:
        pass

    @abstractmethod
    def report(self) -> str:
        pass

    def run(self, analysis_context: BugreportAnalysisContext) -> None:
        result = self.analyze(analysis_context)
        analysis_context.set_result(self.name, result)


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
    def run_all(cls, analysis_context: BugreportAnalysisContext) -> None:
        """Run analysis using all plugins"""
        with cls._lock:
            for plugin in cls._plugins:
                plugin.run(analysis_context)

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
            cls._plugins = PluginRepo.resolve_execution_order(cls._plugins)
            print(
                f"Successfully loaded the following plugins: {[plugin.name for plugin in cls._plugins]}"
            )

    @staticmethod
    def resolve_execution_order(plugins: List[BasePlugin]) -> List[BasePlugin]:
        """
        Resolve plugin execution order based on dependencies using a topological sort.
        Raises an Exception if a circular dependency is detected.
        """
        order = []
        visited = {}
        plugin_names = [plugin.name for plugin in plugins]

        def dfs(plugin: BasePlugin):
            if plugin.name in visited:
                if visited[plugin.name] == "temporary":
                    raise Exception(f"Circular dependency detected at {plugin.name}")
                return
            visited[plugin.name] = "temporary"
            for dep_name in plugin.dependencies:
                if dep_name not in plugin_names:
                    raise Exception(
                        f"Missing dependency: {dep_name} for plugin {plugin.name}"
                    )
                # find the one with the name in the list
                dep = next(
                    (p for p in plugins if p.name == dep_name), None
                )
                dfs(dep)
            visited[plugin.name] = "permanent"
            order.append(plugin)

        for plugin in plugins:
            if plugin.name not in visited:
                dfs(plugin)
        return order


PluginRepo.load_plugins()
