import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

REBOOT_RECORD_START = "---------- Abnormal reboot records ----------"
# REBOOT_RECORD_START = "---------- kernel abnormal reboot records ----------"
REBOOT_FRAMEWORK_START = "---------- VM reboot records ----------"
REBOOT_KERNEL_START = "---------- kernel reboot records ----------"
HANG_RECORD_START = "--------- System hang records ---------"
# REBOOT_DETAIL_START = "----------- dgt and det match ---------"
REBOOT_DETAIL_START = "--------dgt and det match--------"
BEGIN_OF_NEXT_SECTION = re.compile(r"-+ ?(\w+)( \w+)* ?-+")


@dataclass
class DumpsysEntry:
    """Represents a single dumpsys entry with service name and collected data"""

    name: str
    data: str


@dataclass
class LocalRebootRecord:

    def __init__(self):
        self.miui_version: str = ""
        self.timestamp: datetime = None
        self.dgt: str = ""
        self.detail: str = ""
        self.process: str = ""
        self.type: str = ""
        self.current_miui_version: str = ""
        self.sum: str = ""
        self.is_kernel_reboot = False
        self.boot_reason: str = ""

    def merge_records(self, that: "LocalRebootRecord"):
        self.miui_version = (
            self.miui_version if len(self.miui_version) > 0 else that.miui_version
        )
        self.timestamp = (
            self.timestamp if self.timestamp is not None else that.timestamp
        )
        self.dgt = self.dgt if len(self.dgt) > 0 else that.dgt
        self.detail = self.detail if len(self.detail) > 0 else that.detail
        self.process = self.process if len(self.process) > 0 else that.process
        self.type = self.type if len(self.type) > 0 else that.type
        self.current_miui_version = (
            self.current_miui_version
            if len(self.current_miui_version) > 0
            else that.current_miui_version
        )
        self.sum = self.sum if len(self.sum) > 0 else that.sum
        self.boot_reason = (
            self.boot_reason if len(self.boot_reason) > 0 else that.boot_reason
        )

    def isOk(self):
        return (
            len(self.miui_version) > 0
            and len(self.timestamp) > 0
            and len(self.dgt) > 0
            and len(self.detail) > 0
            and len(self.process) > 0
            and len(self.type) > 0
        )

    def idDgtValid(self):
        return len("721e786f2f18e400c95d6abc19d0c676") == len(self.dgt)

    def is_vanilla(self) -> bool:
        return self.boot_reason in {"long_power_key", "reboot", "reboot,userrequested"}

    def set_kernel_reboot(self, powerup_reason):
        self.is_kernel_reboot = True
        self.type = powerup_reason

    def is_current_version(self):
        return self.current_miui_version == self.miui_version

    def get_simple_type(self):
        if self.is_je():
            return "JE"
        if self.is_ne():
            return "NE"
        if self.is_watchdog():
            return "SWDT"
        if self.is_ke():
            return "KE"

        return self.type

    def get_summary(self):
        title = "Reboot-"
        title += self.get_simple_type()
        if not self.is_ke():
            title += "-" + self.process
        title += "-" + self.dgt
        return title

    def is_ne(self):
        return "Native Exception" == self.type

    def is_je(self):
        return "Java Exception" == self.type

    def is_ke(self):
        return self.is_kernel_reboot

    def is_watchdog(self):
        # TODO: HALF_Watchdog
        return "Watchdog" == self.type

    def is_same_time(self, other: "LocalRebootRecord"):
        return self.timestamp == other.timestamp

    def __str__(self):
        return (
            f"本地重启记录:\n"
            f"MIUI版本: {self.miui_version}\n"
            f"时间戳: {self.timestamp}\n"
            f"DGT: {self.dgt}\n"
            f"详情: {self.detail}\n"
            f"进程: {self.process}\n"
            f"异常类型: {self.type}\n"
            f"当前MIUI版本: {self.current_miui_version}\n"
            f"summary: {self.sum}\n"
            f"是否是内核重启: {self.is_kernel_reboot}\n"
            f"启动原因: {self.boot_reason}\n"
        )


@dataclass
class MqsServiceDumpsysEntry(DumpsysEntry):
    """Represents a single dumpsys entry with service name and collected data"""

    boot_records: List[LocalRebootRecord] = field(default_factory=list)

    @classmethod
    def parse_line(
        cls, name: str, log_string: str
    ) -> Optional["MqsServiceDumpsysEntry"]:
        """Parse a single line of dumpsys output into a MqsServiceDumpsysEntry object."""
        result = cls(name, log_string)
        lines = log_string.split("\n")
        current_line_index = 0

        # skip header lines to the reboot record section
        def skip_to_next_section(
            lines: List[str], section_start_line: str, current_index: int
        ) -> int:
            while current_index < len(lines) and not lines[current_index].startswith(
                section_start_line
            ):
                current_index += 1
            current_index += 1  # skip the section start line itself
            return current_index

        current_line_index = skip_to_next_section(
            lines, REBOOT_RECORD_START, current_line_index
        )
        entries, current_line_index = MqsServiceDumpsysEntry.parse_reboot_entries(
            lines[current_line_index:], current_line_index
        )
        result.boot_records.extend(entries)
        # print(lines[current_line_index])

        # TODO: we also need to parse the hang records, but we need to have a new
        #       data structure for that. These records are for ANRs, and now we
        #       just focus on the reboots.
        # Now we can store the HANGs into LocalRebootRecord as a temporary solution

        while current_line_index < len(lines):
            new_start = MqsServiceDumpsysEntry.parse_reboot_record(
                lines, current_line_index, result.boot_records
            )
            # Failure
            if new_start == current_line_index:
                break
            current_line_index = new_start

        return result

    @staticmethod
    def parse_reboot_entries(
        lines: List[str], current_line_index: int
    ) -> LocalRebootRecord:
        result = []
        temp_record = LocalRebootRecord()
        for line in lines:
            # print(line)
            if BEGIN_OF_NEXT_SECTION.match(line):
                break

            if line == "------------------------------------":
                result.append(temp_record)
                temp_record = LocalRebootRecord()
            elif line.startswith("kernel reboot") or line.startswith("miui reboot"):
                boot_reason = line.split(":")[1].strip()
                temp_record.boot_reason = boot_reason
                temp_record.is_kernel_reboot = line.startswith("kernel reboot")
            elif line.startswith("record time_stamp"):
                timestamp = datetime.strptime(
                    line.split("record time_stamp :")[1].strip(), "%Y-%m-%d %H:%M:%S"
                )
                temp_record.timestamp = timestamp
            current_line_index += 1

        return result, current_line_index

    @staticmethod
    def parse_reboot_record(
        lines: List[str], current_line_index: int, results: List[LocalRebootRecord]
    ):
        # print(f"Parsing next section: {current_line_index}, {lines[current_line_index]}")
        current = current_line_index
        arecord = LocalRebootRecord()
        record_modified = False
        record_end_line = "------------------------------------"
        while current < len(lines):
            line = lines[current]
            current += 1
            # print(line)
            if BEGIN_OF_NEXT_SECTION.match(line) or line == record_end_line:
                # print("----------------section end--------------------")
                break

            record_modified = True
            if (key := "record time      :") and line.startswith(key):
                arecord.timestamp = datetime.strptime(
                    line[len(key) :], "%Y-%m-%d %H:%M:%S"
                )
                continue
            elif (key := "vm reboot        :") and line.startswith(key):
                arecord.type = line[len(key) :]
                continue
            elif (key := "kernelreboot     :") and line.startswith(key):
                arecord.set_kernel_reboot(line[len(key) :])
                continue
            elif (key := "miui version     :") and line.startswith(key):
                arecord.miui_version = line[len(key) :]
                continue
            elif (key := "os version     :") and line.startswith(key):
                arecord.miui_version = line[len(key) :]
                continue
            elif (key := "process          :") and line.startswith(key):
                arecord.process = line[len(key) :]
                continue
            elif (key := "dgt              :") and line.startswith(key):
                arecord.dgt = line[len(key) :]
                continue
            elif (key := "sum              :") and line.startswith(key):
                arecord.sum = line[len(key) :]
                continue
            elif (key := "zygotepid        :") and line.startswith(key):
                continue
            elif (key := "det              :") and line.startswith(key):
                details = ""
                while current < len(lines):
                    line = lines[current]
                    # print(line)
                    current += 1

                    if line == record_end_line:
                        break

                    details += line + "\n"
                arecord.detail = details
                break  # det is always at the last, so break the loop now

        # find the one with the same timestamp
        if record_modified:
            for i, record in enumerate(results):
                # print(record.timestamp, arecord.timestamp)
                if (
                    abs(record.timestamp - arecord.timestamp).total_seconds() < 5
                    or record.dgt == arecord.dgt
                ):
                    # print("Found existing record with the same timestamp")
                    results[i].merge_records(arecord)
                    break
            else:
                results.append(arecord)

        return current
