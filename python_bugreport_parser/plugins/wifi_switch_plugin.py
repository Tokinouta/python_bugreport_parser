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

    def analyze(self, analysis_context: BugreportAnalysisContext) -> PluginResult:
        """Extract timestamp from bugreport metadata"""
        bugreport_txt: BugreportTxt = analysis_context.bugreport.bugreport.bugreport_txt

        dumpsys = next((s for s in bugreport_txt.sections if s.name == "DUMPSYS"), None)
        wifi_dumpsys: DumpsysEntry = next(
            (s for s in dumpsys.content.entries if s.name == "wifi"),
            None,
        )
        if not wifi_dumpsys:
            return PluginResult(
                [], metadata={"description": "WifiSwitch"}
            )

        for line in wifi_dumpsys.data.splitlines():
            if "setWifiEnabledInternal" in line:
                self.switch_records.append(line)

        return PluginResult(
            self.switch_records, metadata={"description": "WifiSwitch"}
        )

    def report(self) -> str:
        return "\n".join(self.switch_records)
