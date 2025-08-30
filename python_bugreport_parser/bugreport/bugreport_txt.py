import mmap
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from python_bugreport_parser.bugreport.interfaces import LogInterface
from python_bugreport_parser.bugreport.metadata import Metadata
from python_bugreport_parser.bugreport.section import (
    SECTION_BEGIN,
    SECTION_BEGIN_NO_CMD,
    SECTION_END,
    AnrRecordSection,
    DumpsysSection,
    LogcatSection,
    OtherSection,
    Section,
    SystemPropertySection,
)


class BugreportTxt(LogInterface):
    """
    A class to represent the bugreport.txt file and its contents.
    """

    def __init__(self, path: Path):
        self.raw_file = self._mmap_file(path)
        self.metadata = Metadata()
        self.sections: List[Section] = []
        self.error_timestamp: datetime = None
        self.loaded: bool = False

    def set_error_timestamp(self, error_timestamp: datetime) -> None:
        """
        Set the error timestamp.

        Args:
            error_timestamp (datetime): The error timestamp to set.
        """
        self.error_timestamp = error_timestamp

    def get_sections(self) -> List[Section]:
        return self.sections

    @classmethod
    def from_zip(cls, zip_path: Path, feedback_dir: str) -> "BugreportTxt":
        raise NotImplementedError("Method from_zip is not implemented yet")

    @classmethod
    def from_dir(cls, feedback_dir: Path) -> "BugreportTxt":
        raise NotImplementedError("Method from_zip is not implemented yet")

    def load(self) -> None:
        lines = self._read_file()
        self.metadata.parse(lines)
        self.set_error_timestamp(self.metadata.timestamp) # set a default error timestamp

        current_section_lines = []
        section_start = ("", -1)
        for line_num, line in enumerate(
            lines[self.metadata.lines_passed :], start=self.metadata.lines_passed
        ):
            if match := SECTION_END.search(line):
                group = match.group(2)
                self._create_and_add_section(
                    name=group,
                    start_line=(
                        section_start[1] + 1 if section_start[1] != -1 else line_num - 1
                    ),
                    end_line=line_num - 1,
                    lines=current_section_lines,
                )
                section_start = ("", -1)
                current_section_lines = []
            elif (match := SECTION_BEGIN_NO_CMD.search(line)) or (
                match := SECTION_BEGIN.search(line)
            ):
                group = match.group(1)
                # skip BLOCK STAT, since this is not a beginning of a section
                if group == "BLOCK STAT":
                    continue
                # For these sections without an ending line
                if group != section_start[0]:
                    if section_start[1] != -1:
                        self._create_and_add_section(
                            name=section_start[0],
                            start_line=section_start[1],
                            end_line=line_num - 1,
                            lines=current_section_lines,
                        )
                    current_section_lines = []

                section_start = group, line_num
            else:
                current_section_lines.append(line)

        self.sections.sort(key=lambda x: x.start_line)
        self.loaded = True

    def _create_and_add_section(
        self, name: str, start_line: int, end_line: int, lines: List[str]
    ) -> Section:
        if name == "SYSTEM LOG" or name == "EVENT LOG":
            section_content = LogcatSection()
        elif name == "DUMPSYS":
            section_content = DumpsysSection()
        elif name == "SYSTEM PROPERTIES":
            section_content = SystemPropertySection()
        elif "VM TRACES" in name:
            section_content = AnrRecordSection()
        else:
            section_content = OtherSection()

        current_section = Section(
            name=name,
            start_line=start_line,
            end_line=end_line,
            content=section_content,
        )

        this_year = datetime.now().year
        current_section.parse(
            lines,
            self.metadata.timestamp.year if self.metadata.timestamp else this_year,
        )
        self.sections.append(current_section)
        # print(name, start_line + 1, end_line - 1)

    def _mmap_file(self, path: Path) -> mmap.mmap:
        with open(path, "rb") as f:
            return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

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
