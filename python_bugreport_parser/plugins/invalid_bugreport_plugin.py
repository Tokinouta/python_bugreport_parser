from datetime import datetime

from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.bugreport.dumpsys_entry import MqsServiceDumpsysEntry
from python_bugreport_parser.plugins import (
    BasePlugin,
    BugreportAnalysisContext,
    PluginResult,
)


class InvalidBugreportPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="InvalidBugreportPlugin", dependencies=["TimestampPlugin"]
        )
        self.timestamp = datetime.now()
        self.error_timestamp = datetime.now()
        self.reboot_records = []
        self.is_invalid: bool = False

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> PluginResult:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport.bugreport_txt
        # find the result of TimestampPlugin from analysis_context.results
        result_from_timestamp_plugin = analysis_context.get_result("TimestampPlugin")
        if result_from_timestamp_plugin is None:
            print("Result from TimestampPlugin not found")
            # TODO: return
        # self.timestamp = bugreport.metadata.timestamp
        self.timestamp = analysis_context.get_result("TimestampPlugin")
        self.error_timestamp = bugreport.error_timestamp
        print(self.timestamp, self.error_timestamp)
        dumpsys = next((s for s in bugreport.sections if s.name == "DUMPSYS"), None)
        mqs_dumpsys: MqsServiceDumpsysEntry = next(
            (s for s in dumpsys.content.entries if s.name == "miui.mqsas.MQSService"),
            None,
        )
        reboot_records = mqs_dumpsys.boot_records
        # TODO: if the last reboot is valid, then report this
        candidate_records = [
            record
            for record in reboot_records
            if abs(self.error_timestamp - record.timestamp).total_seconds() < 600
        ]
        self.is_invalid = len(candidate_records) == 0
        self.reboot_records = candidate_records
        return PluginResult(
            self.reboot_records, metadata={"description": "Reboot records"}
        )

    def report(self) -> str:
        # Bugreport timestamp: 2024-08-16T10:02:11
        if self.is_invalid:
            return "Bugreport is invalid\n"
        else:
            report_lines = []
            for record in self.reboot_records:
                report_lines.append(
                    f"Record timestamp: {record.timestamp}, "
                    f"Record reason: {record.boot_reason}, "
                    f"Record type: {record.type}"
                )
            return "\n".join(report_lines)
