import mmap
import re
from pathlib import Path
from typing import List, Optional, Tuple

from python_bugreport_parser.bugreport.metadata import Metadata

# Assume these regex patterns are defined similarly to Rust version
SECTION_END = re.compile(
    r"------ (\d+.\d+)s was the duration of '((.*?)(?: \(.*\))?|for_each_pid\((.*)\))' ------"
)
SECTION_BEGIN = re.compile(r"------ (.*?)(?: \((.*)\)) ------")
SECTION_BEGIN_NO_CMD = re.compile(r"^------ ([^(]+) ------$")


# class Metadata:
#     def __init__(self):
#         self.lines_passed = 0
#         self.timestamp: Optional[str] = None  # Should be a datetime object

#     def parse(self, lines: List[str]) -> None:
#         # Implement metadata parsing logic
#         pass


class SectionContent:
    class LogcatSection:
        def __init__(self, entries: List[str]):
            self.entries = entries

    class Dumpsys:
        def __init__(self):
            self.data = {}

    class Other:
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
        # Implement section parsing logic
        pass


class BugreportTxt:
    def __init__(self, path: Path):
        self.raw_file = self._mmap_file(path)
        self.metadata = Metadata()
        self.sections: List[Section] = []

    def _mmap_file(self, path: Path) -> mmap.mmap:
        with open(path, "r") as f:
            return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    def load(self) -> None:
        matches = self.read_and_slice()
        self.pair_sections(matches)

    def read_and_slice(self) -> List[Tuple[int, str]]:
        try:
            bugreport = self.raw_file.read().decode("utf-8")
        except UnicodeDecodeError:
            bugreport = self.raw_file.read().decode("utf-8", errors="replace")

        lines = bugreport.split(
            "\n"
        )  # splitlines() is not used since there are other characters that may cause wrong linebreaks
        self.metadata.parse(lines)

        matches = []

        def filter_and_add(matches: list, line_number: int, group: str):
            if group == "BLOCK STAT" or group.endswith("PROTO"):
                return
            # print(f"Found {group} at line {line_number}")
            matches.append((line_number, group))

        for line_num, line in enumerate(
            lines[self.metadata.lines_passed :], start=self.metadata.lines_passed
        ):
            if match := SECTION_END.search(line):
                if group := match.group(2):
                    filter_and_add(matches, line_num + 1, group)
            elif match := SECTION_BEGIN.search(line):
                if group := match.group(1):
                    filter_and_add(matches, line_num + 1, group)
            elif match := SECTION_BEGIN_NO_CMD.search(line):
                if group := match.group(1):
                    filter_and_add(matches, line_num + 1, group)

        return matches

    def pair_sections(self, matches: List[Tuple[int, str]]) -> None:
        bugreport = self.raw_file.read().decode("utf-8")
        lines = bugreport.split("\n")
        second_occurrence = False
        FOR_EACH_PID = re.compile(r"for_each_pid\((.*)\)")

        for idx, (line_num, content) in enumerate(matches):
            if idx > 0 and matches[idx - 1][1] in content:
                second_occurrence = True

            if not second_occurrence:
                continue

            prev_line_num, prev_content = matches[idx - 1]
            start_line = prev_line_num
            end_line = line_num

            # workaround for the "for_each_pid" issue
            if start_line + 1 >= end_line:
                continue

            # Create appropriate section content
            if content == "SYSTEM LOG":
                section_content = SectionContent.SystemLog([])
            elif content == "EVENT LOG":
                section_content = SectionContent.EventLog([])
            elif content == "DUMPSYS":
                section_content = SectionContent.Dumpsys()
            else:
                section_content = SectionContent.Other()

            current_section = Section(
                name=content,
                start_line=start_line + 1,
                end_line=end_line - 1,
                content=section_content,
            )

            current_section.parse(
                lines[start_line + 1 : end_line],
                self.metadata.timestamp.year if self.metadata.timestamp else 2023,
            )

            self.sections.append(current_section)
            second_occurrence = False

    def get_sections(self) -> List[Section]:
        return self.sections
