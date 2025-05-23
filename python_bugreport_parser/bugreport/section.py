import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from python_bugreport_parser.bugreport.anr_record import AnrRecord
from python_bugreport_parser.bugreport.dumpsys_entry import (
    MqsServiceDumpsysEntry,
    DumpsysEntry,
)

# Assume these regex patterns are defined similarly to Rust version
SECTION_END = re.compile(
    r"------ (\d+.\d+)s was the duration of '((.*?)(?: \(.*\))?|for_each_pid\((.*)\))' ------"
)
SECTION_BEGIN = re.compile(r"------ (.*?)(?: \((.*)\)) ------")
SECTION_BEGIN_NO_CMD = re.compile(r"^------ ([^(]+) ------$")
LOGCAT_LINE_REGEX = re.compile(
    r"(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) +(\w+) +(\d+) +(\d+) ([A-Z]) ([^:]+) *:(.*)"
)
DUMPSYS_REGEX = re.compile(
    r"--------- \d\.\d+s was the duration of dumpsys (.*), ending at"
)
DUMPSYS_SECTION_DELIMITER = (
    "-------------------------------------------------------------------------------"
)
SYSTEM_PROPERTY_REGEX = re.compile(r"\[([^\]]*)\]: \[([^\]]*)\]", re.DOTALL)


@dataclass
class LogcatLine:
    timestamp: datetime
    user: str
    pid: int
    tid: int
    level: str
    tag: str
    message: str

    @classmethod
    def parse_line(cls, line: str, year: int) -> Optional["LogcatLine"]:
        match = LOGCAT_LINE_REGEX.match(line)
        if not match:
            return None

        time_str = f"{year}-{match.group(1)}"
        try:
            timestamp = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            return None

        return cls(
            timestamp=timestamp,
            user=match.group(2),
            pid=int(match.group(3)),
            tid=int(match.group(4)),
            level=match.group(5),
            tag=match.group(6).strip(),
            message=match.group(7).strip(),
        )

    def __str__(self):
        return (
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')} "
            f"{self.user} {self.pid} {self.tid} {self.level} "
            f"{self.tag}: {self.message}"
        )


class SectionContent(ABC):
    @abstractmethod
    def parse(self, lines: List[str], year: int) -> None:
        """
        Parse sections from lines of text
        Args:
            lines: List of text lines from bugreport
            year: Year context (unused in this implementation)
        """
        pass


class LogcatSection(SectionContent):
    def __init__(self):
        self.entries: List[LogcatLine] = []

    def __len__(self) -> int:
        return len(self.entries)

    def parse(self, lines: List[str], year: int) -> None:
        parsed = [LogcatLine.parse_line(l, year) for l in lines]
        self.entries.extend([p for p in parsed if p is not None])

    def get_line(self, index: int) -> Optional[LogcatLine]:
        try:
            return self.entries[index]
        except IndexError:
            return None

    def search_by_tag(self, tag: str) -> List[LogcatLine]:
        return [line for line in self.entries if line.tag == tag]

    def search_by_time(self, target_time: datetime) -> List[LogcatLine]:
        return [
            line
            for line in self.entries
            if abs(line.timestamp - target_time) <= timedelta(seconds=1)
        ]

    def search_by_level(self, level: str) -> List[LogcatLine]:
        return [line for line in self.entries if line.level == level]

    def search_by_keyword(self, keyword: str) -> List[LogcatLine]:
        return [line for line in self.entries if keyword in line.message]


class DumpsysSection(SectionContent):
    """Container for parsing and storing dumpsys entries from bugreports"""

    def __init__(self):
        self.entries: List[DumpsysEntry] = []

    def parse(self, lines: List[str], year: int) -> None:
        temp = ""
        name = ""
        for line in lines:
            if line == DUMPSYS_SECTION_DELIMITER:
                # When we find a delimiter line, save accumulated data
                if name == "":
                    continue

                if name == "miui.mqsas.MQSService":
                    entry = MqsServiceDumpsysEntry.parse_line(name, temp.strip())
                else:
                    entry = DumpsysEntry(name=match.group(1).strip(), data=temp.strip())
                self.entries.append(entry)
                temp = ""
                name = ""
            elif match := DUMPSYS_REGEX.match(line):
                name = match.group(1).strip()
            elif line.startswith("DUMP OF SERVICE "):
                # We don't need this line, and we get the service name in the previous branch
                # So just skip it
                pass
            else:
                # Accumulate lines between headers
                temp += line + "\n"


class SystemPropertySection(SectionContent):
    def __init__(self):
        self.properties = {}

    def parse(self, lines: List[str], year: int) -> None:
        lines_concated = "\n".join(lines)
        for match in SYSTEM_PROPERTY_REGEX.finditer(lines_concated):
            self.properties[match.group(1)] = match.group(2)


class AnrRecordSection(SectionContent):
    def __init__(self):
        self.record: AnrRecord = AnrRecord()

    def parse(self, lines: List[str], year: int) -> None:
        self.record._split_anr_trace("\n".join(lines))


class OtherSection(SectionContent):
    def parse(self, lines, year):
        pass


class Section:
    def __init__(
        self, name: str, start_line: int, end_line: int, content: SectionContent
    ):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.content = content

    def parse(self, lines: List[str], year: int) -> None:
        self.content.parse(lines, year)

    def get_line_numbers(self) -> int:
        return self.end_line - self.start_line + 1

    def search_by_tag(self, tag: str) -> Optional[List["LogcatLine"]]:
        if isinstance(self.content, LogcatSection):
            return [line for line in self.content.entries if line.tag == tag]
        return None

    def search_by_time(self, time_str: str) -> Optional[List["LogcatLine"]]:
        try:
            target_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            if isinstance(self.content, LogcatSection):
                return [
                    line
                    for line in self.content.entries
                    if abs(line.timestamp - target_time).total_seconds() <= 1
                ]
            return None
        except ValueError:
            return None

    def __str__(self) -> str:
        return f"{self.name}, start: {self.start_line}, end: {self.end_line}"
