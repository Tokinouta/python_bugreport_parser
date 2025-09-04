from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type, Any
from typing import Optional

class LogFileInterface(ABC):
    @classmethod
    @abstractmethod
    def from_zip(cls: Type['LogFileInterface'], zip_path: Path, feedback_dir: Path) -> Optional['LogFileInterface']:
        """Create an instance from a zip file."""
        pass

    @classmethod
    @abstractmethod
    def from_dir(cls: Type['LogFileInterface'], feedback_dir: Path) -> Optional['LogFileInterface']:
        """Create an instance from a directory."""
        pass

class LogLoadable(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load and process the log data."""
        pass