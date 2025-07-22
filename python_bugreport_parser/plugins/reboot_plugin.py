from datetime import datetime

from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.bugreport.dumpsys_entry import (
    LocalRebootRecord,
    MqsServiceDumpsysEntry,
)
from python_bugreport_parser.plugins import (
    BasePlugin,
    BugreportAnalysisContext,
    PluginResult,
)


class RebootPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="RebootPlugin", dependencies=None)
        self.reboot_records = []

    def version(self) -> str:
        return "1.0.0"

    def analyze(self, analysis_context: BugreportAnalysisContext) -> PluginResult:
        """Extract timestamp from bugreport metadata"""
        bugreport: BugreportTxt = analysis_context.bugreport.bugreport.bugreport_txt

        dumpsys = next((s for s in bugreport.sections if s.name == "DUMPSYS"), None)
        mqs_dumpsys: MqsServiceDumpsysEntry = next(
            (s for s in dumpsys.content.entries if s.name == "miui.mqsas.MQSService"),
            None,
        )
        reboot_records = mqs_dumpsys.boot_records
        minidump_records = analysis_context.bugreport.bugreport.dumpstate_board.mini_dump_records
        augmented = []
        for minidump_record in minidump_records:
            min_index, min_time_diff = -1, 10000000000
            new_record = LocalRebootRecord()
            new_record.timestamp = minidump_record.timestamp
            new_record.miui_version = minidump_record.version
            new_record.boot_reason = minidump_record.crash_reason.strip()
            new_record.detail = minidump_record.crash_details.strip()
            new_record.is_kernel_reboot = True
            for i, reboot_record in enumerate(reboot_records):
                if (
                    abs(
                        minidump_record.timestamp - reboot_record.timestamp
                    ).total_seconds()
                    < min_time_diff
                ):
                    min_time_diff = abs(
                        minidump_record.timestamp - reboot_record.timestamp
                    ).total_seconds()
                    min_index = i
            if (
                min_index != -1
                and min_index not in augmented
                and reboot_records[min_index].is_kernel_reboot
            ):
                reboot_records[min_index].merge_records(new_record)
                augmented.append(min_index)
            else:
                reboot_records.append(new_record)

        self.reboot_records = sorted(
            reboot_records,
            key=lambda x: x.timestamp,
        )
        return (
            PluginResult(
                self.reboot_records, metadata={"description": "RebootRecords"}
            ),
        )

    def report(self) -> str:
        return "\n".join([str(record) for record in self.reboot_records])
