import re
from datetime import datetime, timedelta
from typing import Iterator, Optional

# Compile regex patterns once
UPTIME_REGEX = re.compile(r"up (\d+) weeks?, (\d+) days?, (\d+) hours?, (\d+) minutes?")
VERSION_REGEX = re.compile(r"Build fingerprint: '(.*)/(.*)/(.*)/(.*)/(.*):(.*)/(.*)'")


class Metadata:
    def __init__(self):
        self.timestamp: datetime = datetime.now()
        self.version: str = ""
        self.product: str = ""
        self.uptime: timedelta = timedelta()
        self.lines_passed: int = 0

    def parse(self, lines: Iterator[str]) -> None:
        """Parse metadata from bugreport lines"""
        lines_iter = iter(lines)
        while True:
            line = self.advance_line(lines_iter)
            if line is None:
                break

            if line.startswith("== dumpstate: "):
                self.timestamp = self.parse_timestamp(line)
            elif line.startswith("Build fingerprint:"):
                self.version, self.product = self.parse_version_and_product(line)
            elif line.startswith("Uptime:"):
                self.uptime = self.parse_uptime(line)
                break  # Stop after parsing uptime

    def advance_line(self, lines_iter: Iterator[str]) -> Optional[str]:
        """Get next line and increment counter"""
        try:
            line = next(lines_iter).strip()
            self.lines_passed += 1
            return line
        except StopIteration:
            return None

    @staticmethod
    def parse_timestamp(line: str) -> datetime:
        """Parse timestamp from dumpstate line"""
        timestamp_str = line.split("== dumpstate: ", 1)[1].strip()
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e

    @staticmethod
    def parse_version_and_product(line: str) -> str:
        """Extract version and product from build fingerprint"""
        match = VERSION_REGEX.match(line)
        if not match:
            raise ValueError(f"Invalid version line: {line}")
        return match.group(5), match.group(2)

    @staticmethod
    def parse_uptime(line: str) -> timedelta:
        """Convert uptime string to timedelta"""
        uptime_str = line.split("Uptime:", 1)[1].strip()
        match = UPTIME_REGEX.match(uptime_str)
        if not match:
            raise ValueError(f"Invalid uptime format: {uptime_str}")

        weeks = int(match.group(1))
        days = int(match.group(2))
        hours = int(match.group(3))
        minutes = int(match.group(4))

        total_days = weeks * 7 + days
        total_seconds = hours * 3600 + minutes * 60

        return timedelta(days=total_days, seconds=total_seconds)
