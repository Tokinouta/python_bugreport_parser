from typing import List
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod

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


@dataclass
class DumpsysEntry:
    """Represents a single dumpsys entry with service name and collected data"""

    name: str
    data: str


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
    def __init__(self, lines: List[LogcatLine] = None):
        self.entries = lines or []

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

    def parse(self, lines: List[str], _year: int) -> None:

        temp = ""
        for line in lines:
            if match := DUMPSYS_REGEX.match(line):
                # When we find a dumpsys header line, save accumulated data
                self.entries.append(
                    DumpsysEntry(name=match.group(1).strip(), data=temp.strip())
                )
                temp = ""
            else:
                # Accumulate lines between headers
                temp += line + "\n"


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
        if isinstance(self.content, LogcatSection):
            self.content.parse(lines, year)
        elif isinstance(self.content, DumpsysSection):
            self.content.parse(lines, year)
        else:
            self.content.parse(lines, year)

    def get_line_numbers(self) -> int:
        return self.end_line - self.start_line + 1

    def search_by_tag(self, tag: str) -> Optional[List["LogcatLine"]]:
        if isinstance(self.content, LogcatSection):
            return [line for line in self.content.section.lines if line.tag == tag]
        return None

    def search_by_time(self, time_str: str) -> Optional[List["LogcatLine"]]:
        try:
            target_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            if isinstance(self.content, LogcatSection):
                return [
                    line
                    for line in self.content.section.lines
                    if abs(line.timestamp - target_time).total_seconds() <= 1
                ]
            return None
        except ValueError:
            return None

    def __str__(self) -> str:
        return f"{self.name}, start: {self.start_line}, end: {self.end_line}"
