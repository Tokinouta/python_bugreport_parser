from datetime import datetime

from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.plugins import BasePlugin, BugreportAnalysisContext, PluginResult


class AnrDigestPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="AnrDigestPlugin", dependencies=None)
        self.timestamp = datetime.now()

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport_txt
        # Extract all am_anr lines
        # Extract 'ANR in' segment and parse it
        # Match each 'ANR in' segment with the am_anr lines
        #   There maybe some am_anr lines without any 'ANR in' segment
        #   match the one with the same process and nearest timestamp
        analysis_context.set_result(
            self.name,
            PluginResult(
                self.timestamp, metadata={"description": "ANR digest"}
            ),
        )

    def report(self) -> str:
        # Bugreport timestamp: 2024-08-16T10:02:11
        return f"Bugreport timestamp: {self.timestamp.isoformat()}"
