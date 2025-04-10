from datetime import datetime

from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.bugreport.dumpsys_entry import (
    DumpsysEntry,
    LocalRebootRecord,
    MqsServiceDumpsysEntry,
)
from python_bugreport_parser.plugins import (
    BasePlugin,
    BugreportAnalysisContext,
    PluginResult,
)


class WifiSwitchPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="WifiSwitchPlugin", dependencies=None)
        self.switch_records = []

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> None:
        """Extract timestamp from bugreport metadata"""
        bugreport_txt: BugreportTxt = analysis_context.bugreport.bugreport_txt

        dumpsys = next((s for s in bugreport_txt.sections if s.name == "DUMPSYS"), None)
        wifi_dumpsys: DumpsysEntry = next(
            (s for s in dumpsys.content.entries if s.name == "wifi"),
            None,
        )
        for line in wifi_dumpsys.data.splitlines():
            if "setWifiEnabledInternal" in line:
                self.switch_records.append(line)

        analysis_context.set_result(
            self.name,
            PluginResult(self.switch_records, metadata={"description": "RebootRecords"}),
        )

    def report(self) -> str:
        return "\n".join(self.switch_records)
