import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

THERMAL_LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{2}-\d{2} \d{2}:\d{2}:\d{2})\[(?P<tag>[^\]]+)\]\[VIRTUAL-SENSOR-FORMULA (?P<temperature>\d+)\] \{\s*(?P<kv_pairs>(\[[^\[\]]+\]\s*)+)\}"
)

THERMAL_KV_PATTERN = re.compile(r"\[(?P<key>[^\[\] ]+)\s+(?P<value>[^\[\] ]+)\]")


@dataclass
class MiniDumpRecord:
    index: str = ""
    version: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    crash_reason: str = ""
    crash_details: str = ""

    @classmethod
    def parse(cls, data: str) -> Optional["MiniDumpRecord"]:
        """
        Parse the mini dump record from the provided data string.

        :param data: The data string to parse.
        """
        # Example parsing logic (to be customized based on actual data format)
        # print("data", data, "data type", type(data))
        if not data.strip() or data.find("|") == -1:
            return None
        # Assuming the data format is "version_index|timestamp|crash_reason|crash_details"
        print(data)
        version_index, timestamp_str, crash_reason, crash_details = data.split("|")
        index, version = version_index.split(" ")

        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        return cls(
            index=index,
            version=version,
            timestamp=timestamp,
            crash_reason=crash_reason,
            crash_details=crash_details,
        )

    def __str__(self):
        """
        Return a string representation of the MiniDumpRecord object.

        :return: String representation of the object.
        """
        return (
            f"MiniDumpRecord(index={self.index}, version={self.version}, "
            f"timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"crash_reason={self.crash_reason}, "
            f"crash_details={self.crash_details})"
        )


@dataclass
class ThermalRecord:
    """
    Class to represent a thermal record.
    """

    timestamp: datetime = field(default_factory=datetime.now)
    tag: str = ""
    temperatures: Dict[str, int] = field(default_factory=dict)

    def __str__(self):
        """
        Return a string representation of the ThermalRecord object.

        :return: String representation of the object.
        """
        return (
            f"ThermalRecord(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"tag={self.tag})"
        )

    @classmethod
    def parse(cls, line: str) -> Optional["ThermalRecord"]:
        match = THERMAL_LOG_PATTERN.match(line)
        if not match:
            return None

        instance = cls()
        instance.tag = match.group("tag")
        instance.timestamp = datetime.strptime(
            match.group("timestamp"), "%m-%d %H:%M:%S"
        )
        instance.temperatures = dict()
        instance.temperatures["virtual_sensor"] = int(match.group("temperature"))

        kv_pairs_str = match.group("kv_pairs")
        for kv_match in THERMAL_KV_PATTERN.finditer(kv_pairs_str):
            key = kv_match.group("key")
            value = int(kv_match.group("value"))  # Assume all values are integers
            instance.temperatures[key] = value

        return instance


class DumpstateBoard:
    """
    Class to represent the dumpstate board information.
    """

    def __init__(self):
        """
        Initialize the DumpstateBoard object with data.

        :param data: The data to initialize the object with.
        """
        self.sections: List[str] = []
        self.mini_dump_records: List[MiniDumpRecord] = []
        self.kernel_log: str = ""
        self.temperature_log: List[ThermalRecord] = []

    def __repr__(self):
        """
        Return a string representation of the DumpstateBoard object.

        :return: String representation of the object.
        """
        return f"DumpstateBoard(data={self.data})"

    def load(self, dumpstate_board_path: Path) -> None:
        """
        Load the dumpstate board data from the specified directory.

        :param dumpstate_board_dir: Path to the dumpstate board directory.
        """

        pattern = re.compile(r"^------ ([\w ]+) \(.*\)")
        sections = []
        current_name = None
        current_content = []

        with open(dumpstate_board_path, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                # print(line)
                match = pattern.match(line)
                if match:
                    # Save the current section if there's any content or a name
                    if current_name is not None or current_content:
                        sections.append((current_name, current_content))
                        if current_name == "minidump history":
                            self.parse_minidump_history(current_content)
                        elif current_name == "THERMAL DUMP LOG":
                            self.parse_thermal_log(current_content)
                        current_content = []
                    current_name = match.group(1)
                else:
                    current_content.append(line)
            # Add the last section after the loop ends
            if current_name is not None or current_content:
                sections.append((current_name, current_content))
        self.sections = sections
        # print("minidump history ", "\n".join([str(record) for record in self.mini_dump_records]))

    def parse_minidump_history(self, current_content) -> None:
        """
        Parse the mini dump history from the loaded data.
        """
        for record in current_content:
            parsed_record = MiniDumpRecord.parse(record)
            if parsed_record:
                self.mini_dump_records.append(parsed_record)

    def parse_thermal_log(self, current_content) -> None:
        """
        Parse the thermal log from the loaded data.
        """
        for line in current_content:
            parsed_record = ThermalRecord.parse(line)
            if parsed_record:
                self.temperature_log.append(parsed_record)

    def draw_temp_graph(self) -> None:
        x_data = [
            record.timestamp
            for record in self.temperature_log
            if record.tag == "SS-CPU0"
        ]
        y_data = [
            record.temperatures["virtual_sensor"]
            for record in self.temperature_log
            if record.tag == "SS-CPU0"
        ]

        _, ax = plt.subplots(figsize=(10, 4))

        # Plotting
        ax.scatter(x_data, y_data)

        # Set formatter for x-axis
        date_format = mdates.DateFormatter("%m-%d %H:%M:%S")
        ax.xaxis.set_major_formatter(date_format)
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=240))

        plt.grid(True)
        plt.title("Thermal Log")
        plt.xlabel("Time")
        plt.ylabel("Temperature")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("temp.png")
