import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from dateutil.parser import isoparse

PROCESS_INFO_PATTERN = re.compile(
    r"----- (Waiting Channels: )?pid (?P<pid>\d+) at (?P<timestamp>[\d\-:\.\+ ]+)\s+-----"
)
THREAD_SPLIT_PATTERN = re.compile(r'"(?P<thread_name>.*?)"[\s\S]*?\n\n', re.MULTILINE)
NATIVE_FRAME_PATTERN = re.compile(
    r"^\s*(native:\s*)?#(?P<frame_number>\d{2}) pc (?P<pc_address>[0-9a-f]+)\s+(?P<library_path>\S+)\s+(?:\((?P<symbol_name>.+?)\))?\s+(?:\(BuildId: (?P<build_id>[^\)]+)\))?",
)
JAVA_FRAME_PATTERN = re.compile(r"^\s*at\s+(?P<frame>.*?)$")
LOCK_PATTERN = re.compile(
    r"^\s*- (waiting on|waiting to lock|locked)\s+<(?P<lock_address>0x[0-9a-f]+)>\s?(\(.*\))?",
)


class AnrTrace:
    """
    Class to parse and analyze ANR (Application Not Responding) traces of a single process.
    """

    def __init__(self):
        self.is_valid = False  # if there are no stack traces, this is False
        self.pid: int = 0
        self.timestamp: datetime = datetime.now()
        self.cmd_line: str = ""
        self.build_fingerprint: str = ""
        self.abi: str = ""
        self.build_type: str = ""
        self.waiting_threads: Dict[str, List[str]] = defaultdict(list)
        self.holding_threads: Dict[str, List[str]] = defaultdict(list)
        self.threads: List[dict] = []

    def __str__(self):
        return (
            f"pid: {self.pid}\n"
            f"timestamp: {self.timestamp}\n"
            f"cmd_line: {self.cmd_line}\n"
            f"build_fingerprint: {self.build_fingerprint}\n"
            f"abi: {self.abi}\n"
            f"build_type: {self.build_type}\n"
            f"waiting_threads: {self.waiting_threads}\n"
            f"holding_threads: {self.holding_threads}\n"
            f"threads: {self.threads}\n"
        )

    @property
    def process_info(self):
        return {
            "pid": self.pid,
            "timestamp": self.timestamp,
            "cmd_line": self.cmd_line,
            "build_fingerprint": self.build_fingerprint,
            "abi": self.abi,
            "build_type": self.build_type,
        }

    @classmethod
    def from_raw_str(cls, raw_str: str) -> "AnrTrace":
        instance = cls()
        instance.parse_process_info(raw_str)
        instance.parse_threads(raw_str)
        return instance

    # Function to parse the process information
    def parse_process_info(self, file_content: str):
        lines = file_content.strip().split("\n")

        if (match := PROCESS_INFO_PATTERN.search(lines[0])) and match:
            self.is_valid = "Waiting Channel" not in lines[0]

            self.pid = int(match.group("pid"))
            self.timestamp = isoparse(match.group("timestamp"))
            for line in lines[1:]:
                if line.startswith("DALVIK THREADS") or len(line) == 0:
                    break

                if line.startswith("Cmd line: "):
                    self.cmd_line = line.split("Cmd line: ")[1]
                elif line.startswith("Build fingerprint: "):
                    self.build_fingerprint = line.split("Build fingerprint: ")[1]
                elif line.startswith("ABI: "):
                    self.abi = line.split("ABI: ")[1]

    # Function to parse all threads and lock contentions
    def parse_threads(self, file_content: str) -> None:
        print(f"is_valid: {self.is_valid}")
        if not self.is_valid:
            lines = file_content.strip().split("\n")

            # Skip the first lines and find the first empty line to the threads
            lines_passed = 0
            for i, line in enumerate(lines):
                if line.strip() == "":
                    lines_passed = i
                    break
            lines_passed += 1

            for line in lines[lines_passed:]:
                # print(line)
                if line.strip() == "":
                    break

                metadata = {}
                frames = []
                elements = line.split(" ")
                for element in elements:
                    # print(element)
                    if element.find("=") >= 0:
                        key, val = element.split("=")
                        metadata[key] = val.strip('"')
                    elif len(element) > 0:
                        frames.append(element.strip())
                # print(frames, metadata)
                self.threads.append(
                    {
                        "thread_name": "unknown",
                        "metadata": metadata,
                        "frames": frames,
                        "lock_info": [],
                    }
                )
            return

        # Split the content into thread stacks based on thread name
        # thread_contents = THREAD_SPLIT_PATTERN.split(file_content.strip())
        # print(f"len of thread_contents: {len(thread_contents)}")

        for thread_content in THREAD_SPLIT_PATTERN.finditer(file_content):
            # print(thread_content)
            if not thread_content:
                continue

            content = thread_content.group(0)
            # Parse individual thread stack
            thread_name, metadata, frames, lock_info = self.parse_thread_stack(content)

            # Track waiting and holding threads for locks
            for lock_status, lock_address, _ in lock_info:
                if lock_status == "waiting to lock":
                    self.waiting_threads[lock_address].append(thread_name)
                elif lock_status == "locked":
                    self.holding_threads[lock_address].append(thread_name)

            self.threads.append(
                {
                    "thread_name": thread_name,
                    "metadata": metadata,
                    "frames": frames,
                    "lock_info": lock_info,
                }
            )

    # Function to parse thread metadata and frames
    def parse_thread_stack(self, thread_content: str) -> tuple:
        # Extract thread name
        # TODO: parse additional information in this line
        thread_name_pattern = re.compile(r'"(?P<thread_name>.*?)"')
        # line_of_thread_start = 0
        # for i, line in enumerate(thread_content.split("\n")):
        # thread_content = "\n".join(thread_content.split("\n")[line_of_thread_start:])

        lines = thread_content.split("\n")
        metadata = {}
        frames = []
        lock_info = []
        thread_name = "unknown"
        for i, line in enumerate(lines):
            # print(line)
            if (match := thread_name_pattern.match(line)) and match:
                thread_name = match.group("thread_name")
            elif line.find("|") >= 0:
                for match in re.finditer(r'(\S+)=(".*?"|\(.*?\)|\S+)', line):
                    key, val = match.groups()
                    # print(key, val)
                    metadata[key] = val.strip('"')  # remove quotes if present
            elif (match := NATIVE_FRAME_PATTERN.match(line)) and match:
                frame = {
                    "frame_number": match.group("frame_number"),
                    "pc_address": match.group("pc_address"),
                    "library_path": match.group("library_path"),
                    "symbol_name": match.group("symbol_name"),
                    "build_id": match.group("build_id"),
                }
                frames.append(frame)  # Extract frames (at lines)
            elif (match := JAVA_FRAME_PATTERN.match(line)) and match:
                frames.append(match.group("frame").strip())
            elif (match := LOCK_PATTERN.match(line)) and match:
                lock_status = match.group(1).strip()
                lock_address = match.group(2).strip()
                lock_object = match.group(3).strip("()")
                # print("lock: ", lock_status, lock_address)
                lock_info.append((lock_status, lock_address, lines[i - 1].strip()))
                frames[-1] += f"{lock_status} on lock {lock_address} ({lock_object})"

        return thread_name, metadata, frames, lock_info

    # Function to display parsed thread and lock information
    def display_thread_and_lock_info(self):
        print("Process Information:")
        for key, value in self.process_info.items():
            print(f"{key}: {value}")
        print("-" * 40)

        print("\nThread Stack Report:")
        for thread in self.threads:
            print(f"\nThread Name: {thread["thread_name"]}")
            print("Metadata:")
            for key, value in thread["metadata"].items():
                print(f"  {key}: {value}")

            print("Frames:")
            for frame in thread["frames"]:
                print(f"  {frame}")

            print("Lock Information:")
            for lock_status, lock_address, _ in thread["lock_info"]:
                print(f"  {lock_status} on lock 0x{lock_address}")

        print("\nLock Contentions Report:")
        for lock_address in set(self.waiting_threads.keys()).union(
            set(self.holding_threads.keys())
        ):
            holding = self.holding_threads.get(lock_address, [])
            waiting = self.waiting_threads.get(lock_address, [])

            if holding:
                print(f"Lock {lock_address} is held by: {", ".join(holding)}")

            if waiting:
                print(f"Lock {lock_address} is being waited by: {", ".join(waiting)}")
            print("-" * 40)


class AnrRecord:
    def __init__(self):
        self.type = ""  # ANR, scout hang, scout warning
        self.traces: List[AnrTrace] = []

    # Function to split the ANR trace file into sections based on the given pattern
    def split_anr_trace(self, file_content):
        # Regex pattern to match each section, including the delimiter lines
        section_pattern = re.compile(
            r"----- (pid \d+|Waiting Channels: pid \d+) at [\d\-:\.\+ ]+ -----.*?----- end \d+ -----",
            re.DOTALL,
        )

        # Find all sections that match the pattern
        sections = section_pattern.findall(file_content)
        print(len(sections))

        # Collect the matched sections
        for match in section_pattern.finditer(file_content):
            # Append the section as a whole (including delimiter lines)
            section_content = match.group(0) if match else ""
            # print(type(section_content), len())
            self.traces.append(AnrTrace.from_raw_str(section_content))
