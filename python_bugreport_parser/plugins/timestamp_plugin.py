from datetime import datetime
from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.plugins import BasePlugin, BugreportAnalysisContext


class TimestampPlugin(BasePlugin):
    def __init__(self):
        self.timestamp = datetime.now()

    def name(self) -> str:
        return "TimestampPlugin"

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport_txt
        self.timestamp = bugreport.metadata.timestamp
        # print(f"Analyzed timestamps: {self.timestamp}")

    def report(self) -> str:
        # Bugreport timestamp: 2024-08-16T10:02:11
        return f"Bugreport timestamp: {self.timestamp.isoformat()}"
