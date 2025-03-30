import mmap
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from python_bugreport_parser.bugreport.metadata import Metadata
from python_bugreport_parser.bugreport.section import (
    SECTION_BEGIN,
    SECTION_BEGIN_NO_CMD,
    SECTION_END,
    DumpsysSection,
    LogcatSection,
    OtherSection,
    Section,
    SystemPropertySection,
)


class BugreportTxt:
    def __init__(self, path: Path):
        self.raw_file = self._mmap_file(path)
        self.metadata = Metadata()
        self.sections: List[Section] = []

    def _mmap_file(self, path: Path) -> mmap.mmap:
        with open(path, "rb") as f:
            return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    def load(self) -> None:
        matches = self.read_and_slice()
        self.pair_sections(matches)

    def read_and_slice(self) -> List[Tuple[int, str]]:
        lines = self._read_file()

        self.metadata.parse(lines)

        matches = []

        def filter_and_add(matches: list, line_number: int, group: str):
            if group == "BLOCK STAT" or group.endswith("PROTO"):
                return
            matches.append((line_number, group))

        for line_num, line in enumerate(
            lines[self.metadata.lines_passed :], start=self.metadata.lines_passed
        ):
            if match := SECTION_END.search(line):
                if group := match.group(2):
                    filter_and_add(matches, line_num, group)
            elif match := SECTION_BEGIN.search(line):
                if group := match.group(1):
                    filter_and_add(matches, line_num, group)
            elif match := SECTION_BEGIN_NO_CMD.search(line):
                if group := match.group(1):
                    filter_and_add(matches, line_num, group)

        return matches

    def pair_sections(self, matches: List[Tuple[int, str]]) -> None:
        lines = self._read_file()
        second_occurrence = False

        for idx, (line_num, content) in enumerate(matches):
            if idx > 0 and matches[idx - 1][1] in content:
                second_occurrence = True

            if not second_occurrence:
                continue

            prev_line_num, _ = matches[idx - 1]
            start_line = prev_line_num
            end_line = line_num

            # workaround for the "for_each_pid" issue
            if start_line + 1 >= end_line:
                continue

            # Create appropriate section content
            if content == "SYSTEM LOG" or content == "EVENT LOG":
                section_content = LogcatSection()
            elif content == "DUMPSYS":
                section_content = DumpsysSection()
            elif content == "SYSTEM PROPERTIES":
                section_content = SystemPropertySection()
            else:
                section_content = OtherSection()

            current_section = Section(
                name=content,
                start_line=start_line + 1,
                end_line=end_line - 1,
                content=section_content,
            )

            this_year = datetime.now().year
            current_section.parse(
                lines[start_line + 1 : end_line],
                self.metadata.timestamp.year if self.metadata.timestamp else this_year,
            )

            self.sections.append(current_section)
            second_occurrence = False

    def get_sections(self) -> List[Section]:
        return self.sections

    def _read_file(self) -> List[str]:
        """
        Reads the content of the raw file, decodes it using UTF-8, and handles any encoding errors by replacing invalid characters.

        Returns:
            List[str]: A list of strings where each string represents a line from the file.

        Notes:
            - The file pointer is reset to the beginning after reading.
            - Lines are split using the newline character ("\n") instead of `splitlines()` to avoid issues with non-standard linebreak characters.
        """
        content = self.raw_file.read().decode("utf-8", errors="replace")
        self.raw_file.seek(0)  # Reset the file pointer to the beginning

        # splitlines() is not used since there are other characters that may cause wrong linebreaks
        lines = content.split("\n")
        return lines
