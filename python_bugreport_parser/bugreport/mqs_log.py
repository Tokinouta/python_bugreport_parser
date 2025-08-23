"""
This log is separated by '------ (.*) in \d+s ------' and contains multiple entries.
The above line is the start of a new section, and no explicit end is defined.
"""

import re
from enum import Enum
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, DefaultDict, Pattern

from python_bugreport_parser.utils import unzip_and_delete

SECTION_RE: Pattern[str] = re.compile(r"^-+ \((.*?)\) in (\d+s) -+$")
HEADER_RE: Pattern[str] = re.compile(r"^==\s*(.*?):\s*(.*?)\s*$")


class LogType(Enum):
    """
    Enumeration of different log types in the system.
    """

    UNKNOWN = "unknown"
    JAVA_CRASH = "javacrash"
    NATIVE_CRASH = "nativecrash"
    WATCHDOG = "watchdog"
    MQS_LOG = "mqs_log"

    @classmethod
    def from_string(cls, type_str: str) -> "LogType":
        """
        Convert a string to LogType enum value.

        Args:
            type_str: The string representation of the log type

        Returns:
            The corresponding LogType enum value.
            If the string doesn't match any LogType,
            LogType.UNKNOWN will be returned.
        """
        try:
            return cls(type_str)
        except ValueError as _:
            return LogType.UNKNOWN


class MqsLog:
    """
    Class to parse MQS logs.
    """

    log_data: Optional[str]
    type: LogType

    def __init__(self, log_data: Optional[str]) -> None:
        """
        Initialize the MqsLog with log data.

        :param log_data: The raw log data to be parsed.
        """
        self.log_data = log_data
        self.type = LogType.JAVA_CRASH

    @classmethod
    def from_zip(cls, zip_file: Path, unzip_dir: Path):
        """
        Create an instance of MqsLog from a zip file.

        :param zip_file: The zip file containing the log.
        :return: An instance of MqsLog.
        """
        unzip_and_delete(zip_file, unzip_dir)
        return MqsLog.from_dir(unzip_dir)

    @classmethod
    def from_dir(cls, log_dir: Path):
        """
        Create an instance of MqsLog from a directory.

        :param log_dir: The directory containing the log file.
        """
        instance = cls(None)
        log_file = next((log_dir.glob("-1*.txt")), None)
        if not log_file:
            raise FileNotFoundError(f"No log file found in {log_dir}")

        instance.log_data = log_file.read_text(encoding="utf-8")
        instance.type = LogType.from_string(str(log_file).split("_")[2])

        instance._parse_txt(instance.log_data)
        instance.load()
        return instance

    def _parse_txt(
        self, file_content: str
    ) -> Dict[str, Dict[str, str] | DefaultDict[str, List[str]]]:
        """
        Parse the text file in MQS log data.

        :param file_content: Content of the log file to parse.
        :return: Parsed log data as a dictionary with header and sections.
        """
        lines = file_content.strip().splitlines()

        result: Dict[str, Dict[str, str] | DefaultDict[str, List[str]]] = {
            "header": {},
            "sections": defaultdict(list),
        }

        current_section: Optional[str] = None
        in_header = True

        for line in lines:
            if in_header:
                if line.startswith("===") or not line.strip():
                    continue
                header_match = HEADER_RE.match(line)
                if header_match:
                    key, value = header_match.groups()
                    result["header"][key] = value
                else:
                    in_header = False  # switch to section parsing
            if not in_header:
                section_match = SECTION_RE.match(line)
                if section_match:  # case for the section delimiter
                    current_section, _ = section_match.groups()  # _ for unused duration
                    result["sections"][current_section].append(line)
                elif current_section:
                    result["sections"][current_section].append(line)

        return result

    def load(self) -> None:
        """
        Load and parse the MQS log data that was previously set.
        This method should be called after the log_data has been set.
        """
        if self.log_data is None:
            raise ValueError(
                "No log data has been set. Set log_data before calling load()."
            )
