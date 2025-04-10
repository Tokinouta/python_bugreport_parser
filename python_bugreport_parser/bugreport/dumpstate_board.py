from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path
import re
from typing import List


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
        if not data.strip():
            return None
        # Assuming the data format is "version_index|timestamp|crash_reason|crash_details"
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
        self.temperature: str = ""

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
        # Assuming the data is in a file named 'dumpstate_board.txt'
        # if dumpstate_board_path.exists():
        #     with open(
        #         dumpstate_board_path, "r", encoding="utf-8", errors="ignore"
        #     ) as file:
        #         self.data = file.read()
        # else:
        #     raise FileNotFoundError(
        #         f"Dumpstate board file not found: {dumpstate_board_path}"
        #     )
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
