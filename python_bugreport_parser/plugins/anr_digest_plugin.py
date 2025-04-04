from datetime import datetime
from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.plugins import BasePlugin


class AnrDigestPlugin(BasePlugin):
    def __init__(self):
        self.timestamp = datetime.now()

    def name(self) -> str:
        return "TimestampPlugin"

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, bugreport: BugreportTxt) -> None:
        """Extract timestamp from bugreport metadata"""
        # Extract all am_anr lines
        # Extract 'ANR in' segment and parse it
        # Match each 'ANR in' segment with the am_anr lines
        #   There maybe some am_anr lines without any 'ANR in' segment
        #   match the one with the same process and nearest timestamp

    def report(self) -> str:
        # Bugreport timestamp: 2024-08-16T10:02:11
        return f"Bugreport timestamp: {self.timestamp.isoformat()}"
