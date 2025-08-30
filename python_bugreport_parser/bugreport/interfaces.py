from abc import ABC, abstractmethod
from typing import Type, Any

class LogInterface(ABC):
    @classmethod
    @abstractmethod
    def from_zip(cls: Type['LogInterface'], zip_path: str, feedback_dir: str) -> 'LogInterface':
        """Create an instance from a zip file."""
        pass

    @classmethod
    @abstractmethod
    def from_dir(cls: Type['LogInterface'], feedback_dir: str) -> 'LogInterface':
        """Create an instance from a directory."""
        pass

    @abstractmethod
    def load(self) -> Any:
        """Load and process the log data."""
        pass