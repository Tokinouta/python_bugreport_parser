import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from dateutil.parser import isoparse


SECTION_PATTERN = re.compile(  # Regex pattern to match each section, including the delimiter lines
    r"----- (pid \d+|Waiting Channels: pid \d+) at [\d\-:\.\+ ]+ -----.*?----- end \d+ -----",
    re.DOTALL,
)
PROCESS_INFO_PATTERN = re.compile(
    r"----- (Waiting Channels: )?pid (?P<pid>\d+) at (?P<timestamp>[\d\-:\.\+ ]+)\s+-----"
)
THREAD_SPLIT_PATTERN = re.compile(r'"(?P<thread_name>.*?)"[\s\S]*?\n\n', re.MULTILINE)
NATIVE_FRAME_PATTERN = re.compile(
    r"^\s*(native:\s*)?#(?P<frame_number>\d{2}) pc (?P<pc_address>[0-9a-f]+)\s+(?P<library_path>\S+)\s+(?:\((?P<symbol_name>.+?)\))?\s+(?:\(BuildId: (?P<build_id>[^\)]+)\))?",
)
JAVA_FRAME_PATTERN = re.compile(
    r"^\s*at\s+(?P<symbol_name>.*?)\((?P<source_code_path>.*)\)$"
)
FAILED_FRAME_PATTERN = re.compile(r"sysTid=(\d+)\s+state=(\w)\s+(\S+)")
THREAD_NAME_PATTERN = re.compile(r'"(?P<thread_name>.*?)"')
LOCK_PATTERN = re.compile(
    r"^\s*- (sleeping on|waiting on|waiting to lock|locked)\s+<(?P<lock_address>0x[0-9a-f]+)>\s?(\(.*\))?",
)


class AnrLockInfo:
    """
    Represents information about a lock inside a certain process
      in an ANR (Application Not Responding) scenario.
    Attributes:
        lock_status (str): The status of the lock (e.g., locked, unlocked).
        lock_address (str): The memory address of the lock.
        lock_object (str): The object that is being waited on.
        holding_threads (List[str]): A list of thread identifiers currently holding the lock.
        waiting_threads (List[str]): A list of thread identifiers currently waiting for the lock.
    """

    def __init__(self):
        self.lock_status: str = ""
        self.lock_address: str = ""
        self.lock_object: str = ""  # the object that is being waited on
        self.holding_threads: List[str] = []  # threads holding the lock
        self.waiting_threads: List[str] = []  # threads waiting for the lock


class AnrThreadFrame:
    """
    Represents a thread frame in an ANR (Application Not Responding) report.

    Attributes:
        is_native_frame (bool): Indicates whether the frame is a native frame.
        frame_number (str): The frame number in the stack trace.
        pc_address (str): The program counter address of the frame.
        library_path (str): The path to the library associated with the frame.
        symbol_name (str): The symbol name associated with the frame.
        build_id (str): The build ID of the library or executable.
        holding_lock (str): Information about the lock held or waiting by the thread at this frame.
    """

    # class HoldingLock:
    #     def __init__(self):
    #         self.lock_address = ""
    #         self.lock_status = ""

    def __init__(self):
        self.is_native_frame: bool = False
        self.frame_number: str = ""
        self.pc_address: str = ""
        self.library_path: str = ""
        self.symbol_name: str = ""
        self.build_id: str = ""
        self.holding_lock: str = ""


class AnrThread:
    """
    Represents a thread involved in an Application Not Responding (ANR) event.
    Attributes:
        name (str): The name of the thread. Defaults to "unknown".
        frames (List[AnrThreadFrame]): A list of stack frames associated with the thread.
        metadata (Dict[str, str]): A dictionary containing metadata about the thread.
        lock_info (List[Tuple[str, str, str]]): A list of tuples representing lock information.
            Each tuple contains:
                - lock_status (str): The status of the lock.
                - lock_address (str): The memory address of the lock.
                - lock_function (str): The function associated with the lock.
    """

    def __init__(self):
        self.name: str = "unknown"
        self.frames: List[AnrThreadFrame] = []
        self.metadata: Dict[str, str] = {}
        self.lock_info: List[Tuple[str, str, str]] = []


class AnrProcess:
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
        self.threads: List[AnrThread] = []
        self.lock_info: Dict[str, AnrLockInfo] = {}

    def __str__(self):
        return (
            f"pid: {self.pid}\n"
            f"timestamp: {self.timestamp}\n"
            f"cmd_line: {self.cmd_line}\n"
            f"build_fingerprint: {self.build_fingerprint}\n"
            f"abi: {self.abi}\n"
            f"threads: {self.threads}\n"
            f"locks: {self.lock_info}\n"
        )

    @property
    def process_info(self):
        return {
            "pid": self.pid,
            "timestamp": self.timestamp,
            "cmd_line": self.cmd_line,
            "build_fingerprint": self.build_fingerprint,
            "abi": self.abi,
        }

    @classmethod
    def from_raw_str(cls, raw_str: str) -> "AnrProcess":
        instance = cls()
        instance.parse_process_info(raw_str)
        instance.parse_threads(raw_str)
        return instance

    # Function to parse the process information
    def parse_process_info(self, file_content: str) -> None:
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
        # print(f"is_valid: {self.is_valid}")
        if not self.is_valid:
            lines = file_content.strip().split("\n")
            for line in lines:
                if (match := FAILED_FRAME_PATTERN.search(line)) and match:
                    frame = AnrThreadFrame()
                    frame.symbol_name = match.group(3)
                    thread = AnrThread()
                    thread.name = "unknown"
                    thread.metadata = {
                        "sysTid": match.group(1),
                        "state": match.group(2),
                    }
                    thread.frames = [frame]
                    thread.lock_info = []
                    self.threads.append(thread)
            return

        for thread_content in THREAD_SPLIT_PATTERN.finditer(file_content):
            # print(thread_content)
            if not thread_content:
                continue

            self.parse_thread_stack(thread_content.group(0))

    # Function to parse thread metadata and frames
    def parse_thread_stack(self, thread_content: str) -> tuple:
        lines = thread_content.split("\n")
        thread = AnrThread()
        for i, line in enumerate(lines):
            if (match := THREAD_NAME_PATTERN.match(line)) and match:
                thread.name = match.group("thread_name")
                for attr in line.split(" "):
                    if attr.find("=") >= 0:
                        key, val = attr.split("=")
                    else:
                        key, val = attr, attr
                    thread.metadata[key] = val.strip('"')
            elif line.find("|") >= 0:
                for match in re.finditer(r'(\S+)=(".*?"|\(.*?\)|\S+)', line):
                    key, val = match.groups()
                    thread.metadata[key] = val.strip('"')  # remove quotes if present
            elif (match := NATIVE_FRAME_PATTERN.match(line)) and match:
                frame = AnrThreadFrame()
                frame.is_native_frame = True
                frame.frame_number = match.group("frame_number")
                frame.pc_address = match.group("pc_address")
                frame.library_path = match.group("library_path")
                frame.symbol_name = match.group("symbol_name")
                frame.build_id = match.group("build_id")
                thread.frames.append(frame)  # Extract frames (at lines)
            elif (match := JAVA_FRAME_PATTERN.match(line)) and match:
                frame = AnrThreadFrame()
                frame.library_path = match.group("source_code_path")
                frame.symbol_name = match.group("symbol_name")
                thread.frames.append(frame)
            elif (match := LOCK_PATTERN.match(line)) and match:
                lock_status = match.group(1).strip()
                lock_address = match.group(2).strip()
                lock_object = match.group(3).strip("()")
                # print("lock: ", lock_status, lock_address)
                if lock_address not in self.lock_info:
                    self.lock_info[lock_address] = AnrLockInfo()
                    self.lock_info[lock_address].lock_address = lock_address
                    self.lock_info[lock_address].lock_object = lock_object

                # Track waiting and holding threads for locks
                if lock_status == "waiting to lock":
                    self.lock_info[lock_address].waiting_threads.append(thread.name)
                elif lock_status == "locked":
                    self.lock_info[lock_address].holding_threads.append(thread.name)

                thread.lock_info.append(
                    (lock_status, lock_address, lines[i - 1].strip())
                )
                thread.frames[-1].holding_lock = (
                    f"{lock_status} lock {lock_address} ({lock_object})"
                )
        self.threads.append(thread)
        # return thread_name, metadata, frames, lock_info

    # Function to display parsed thread and lock information
    def display_thread_and_lock_info(self):
        print("Process Information:")
        for key, value in self.process_info.items():
            print(f"{key}: {value}")
        print("-" * 40)

        print("\nThread Stack Report:")
        for thread in self.threads:
            print(f"\nThread Name: {thread.name}")
            print("Metadata:")
            for key, value in thread.metadata.items():
                print(f"  {key}: {value}")

            print("Frames:")
            for frame in thread.frames:
                print(f"  {frame.symbol_name}, {frame.holding_lock}")

            print("Lock Information:")
            for lock_status, lock, _ in thread.lock_info:
                print(f"  {lock_status} lock 0x{lock}")

        print("\nLock Contentions Report:")
        for lock_address, lock in self.lock_info.items():
            holding = lock.holding_threads
            waiting = lock.waiting_threads

            if holding:
                print(f"Lock {lock_address} is held by: {", ".join(holding)}")

            if waiting:
                print(f"Lock {lock_address} is being waited by: {", ".join(waiting)}")
            print("-" * 40)


class AnrRecord:
    def __init__(self):
        self.type = ""  # ANR, scout hang, scout warning
        self.traces: List[AnrProcess] = []

    # Function to split the ANR trace file into sections based on the given pattern
    # TODO: add a function that can gather all the traces of a single process
    #  across multiple ANR traces, thus providing a more comprehensive view of
    #  the process's state by tracing across time.
    def split_anr_trace(self, file_content):
        # Collect the matched sections
        for match in SECTION_PATTERN.finditer(file_content):
            # Append the section as a whole (including delimiter lines)
            section_content = match.group(0) if match else ""
            # print(type(section_content), len())
            self.traces.append(AnrProcess.from_raw_str(section_content))
