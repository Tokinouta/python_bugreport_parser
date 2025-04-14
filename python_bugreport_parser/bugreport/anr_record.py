from datetime import datetime
import re
from collections import defaultdict
from typing import List


class AnrTrace:
    process_info_pattern = re.compile(
        r"----- (Waiting Channels: )?pid (?P<pid>\d+) at (?P<timestamp>[\d\-:\.\+ ]+)\s+-----"
    )

    process_without_stack_pattern = re.compile(
        r"----- Waiting Channels: pid (?P<pid>\d+) at (?P<timestamp>[\d\-:\.\+ ]+)\s+-----\n"
        r"Cmd line: (?P<cmd_line>.*)\n"
    )

    def __init__(self):
        self.is_valid = False  # if there are no stack traces, this is False
        self.pid = ""
        self.timestamp = ""
        self.cmd_line = ""
        self.build_fingerprint = ""
        self.abi = ""
        self.build_type = ""
        self.thread_metadata: List[dict] = []
        self.thread_frames: List[dict] = []

    # Function to parse the process information
    def parse_process_info(self, file_content: str):
        lines = file_content.split("\n")

        if (match := AnrTrace.process_info_pattern.search(lines[0])) and match:
            self.is_valid = "Waiting channel" not in lines[0]
            self.pid = match.group("pid")
            self.timestamp = datetime.strptime(
                match.group("timestamp"), "%Y-%m-%d %H:%M:%S.%f%z"
            )
            for line in lines[1]:
                if line.startswith("DALVIK THREADS") or len(line) == 0:
                    break

                if line.startswith("Cmd line: "):
                    self.cmd_line = line.split("Cmd line: ")[1]
                elif line.startswith("Build fingerprint: "):
                    self.build_fingerprint = line.split("Build fingerprint: ")[1]
                elif line.startswith("ABI: "):
                    self.abi = line.split("ABI: ")[1]
                elif line.startswith("suspend all histogram"):
                    self.timestamp = line.split("Timestamp: ")[1]

        return None

    # Function to parse thread metadata and frames
    def parse_thread_stack(self, thread_content):
        # Extract thread name
        thread_name_pattern = re.compile(r'"(?P<thread_name>.*?)"')
        line_of_thread_start = 0
        for i, line in enumerate(thread_content.split("\n")):
            if thread_name_pattern.match(line):
                print("current line: ", line)
                line_of_thread_start = i
                break
        thread_content = "\n".join(thread_content.split("\n")[line_of_thread_start:])

        thread_name_match = thread_name_pattern.match(thread_content)
        thread_name = (
            thread_name_match.group("thread_name") if thread_name_match else "Unknown"
        )

        # Extract thread metadata (| lines)
        metadata = {}
        metadata_pattern = re.compile(
            r"^\s*\|\s*(?P<key>[\w\s]+)=\s*(?P<value>.*?)$", re.MULTILINE
        )
        for metadata_match in metadata_pattern.finditer(thread_content):
            key = metadata_match.group("key").strip()
            value = metadata_match.group("value").strip()
            metadata[key] = value

        # Extract frames (at lines)
        frames = []
        frame_pattern = re.compile(r"^\s*at\s+(?P<frame>.*?)$", re.MULTILINE)
        for frame_match in frame_pattern.finditer(thread_content):
            frames.append(frame_match.group("frame").strip())

        # Extract lock information (- lines)
        lock_info = []
        lock_pattern = re.compile(
            r"^\s*- (waiting on|waiting to lock|locked)\s+<(?P<lock_address>[0-9a-f]+)>",
            re.MULTILINE,
        )
        for lock_match in lock_pattern.finditer(thread_content):
            lock_status = lock_match.group(1).strip()
            lock_address = lock_match.group(2).strip()
            lock_info.append((lock_status, lock_address))

        return thread_name, metadata, frames, lock_info

    # Function to parse all threads and lock contentions
    def parse_threads(self, file_content):
        # Split the content into thread stacks based on thread name
        thread_split_pattern = re.compile(
            r'"(?P<thread_name>.*?)"[\s\S]*?\n\n', re.MULTILINE
        )
        thread_contents = thread_split_pattern.split(file_content.strip())
        print(len(thread_contents))

        # Initialize dictionaries to store waiting and holding threads
        waiting_threads = defaultdict(list)
        holding_threads = defaultdict(list)
        threads = []

        for thread_content in thread_split_pattern.finditer(file_content):
            print(thread_content)
            if not thread_content:
                continue

            content = thread_content.group(0)
            # Parse individual thread stack
            thread_name, metadata, frames, lock_info = self.parse_thread_stack(content)

            # Track waiting and holding threads for locks
            for lock_status, lock_address in lock_info:
                if lock_status == "waiting on":
                    waiting_threads[lock_address].append(thread_name)
                elif lock_status == "locked":
                    holding_threads[lock_address].append(thread_name)

            threads.append(
                {
                    "thread_name": thread_name,
                    "metadata": metadata,
                    "frames": frames,
                    "lock_info": lock_info,
                }
            )

        return threads, waiting_threads, holding_threads

    # Function to display parsed thread and lock information
    def display_thread_and_lock_info(
        self, process_info, threads, waiting_threads, holding_threads
    ):
        print("Process Information:")
        for key, value in process_info.items():
            print(f"{key}: {value}")
        print("-" * 40)

        print("\nThread Stack Report:")
        for thread in threads:
            print(f"\nThread Name: {thread['thread_name']}")
            print("Metadata:")
            for key, value in thread["metadata"].items():
                print(f"  {key}: {value}")

            print("Frames:")
            for frame in thread["frames"]:
                print(f"  {frame}")

            print("Lock Information:")
            for lock_status, lock_address in thread["lock_info"]:
                print(f"  {lock_status} on lock 0x{lock_address}")

        print("\nLock Contentions Report:")
        for lock_address in set(waiting_threads.keys()).union(
            set(holding_threads.keys())
        ):
            holding = holding_threads.get(lock_address, [])
            waiting = waiting_threads.get(lock_address, [])

            if holding:
                print(f"Lock 0x{lock_address} is held by: {', '.join(holding)}")

            if waiting:
                print(
                    f"Lock 0x{lock_address} is being waited on by: {', '.join(waiting)}"
                )
            print("-" * 40)


class AnrRecord:
    def __init__(self):
        self.type = ""  # ANR, scout hang, scout warning
        self.traces: List[AnrTrace] = []

    # Function to split the ANR trace file into sections based on the given pattern
    def split_anr_trace(self, file_content):
        # Regex pattern to match each section, including the delimiter lines
        section_pattern = re.compile(
            r"----- (pid \d+|Waiting channel: pid \d+) at [\d\-:\.\+ ]+ -----.*?----- end \d+ -----",
            re.DOTALL,
        )

        # Find all sections that match the pattern
        sections = section_pattern.findall(file_content)

        # Collect the matched sections
        split_sections = []
        for _ in sections:
            # Append the section as a whole (including delimiter lines)
            match = section_pattern.search(file_content)
            split_sections.append(match.group(0))

        return split_sections


# Example usage
if __name__ == "__main__":
    # Load the thread stack content (can be from a file or string)
    thread_stack_content = """
----- pid 2270 at 2024-08-16 10:02:17.932278717+0700 -----
Cmd line: system_server
Build fingerprint: 'Xiaomi/houji_global/houji:14/UKQ1.230804.001/V816.0.12.0.UNCMIXM:user/release-keys'
ABI: 'arm64'
Build type: optimized
suspend all histogram:	Sum: 31.260ms 99% C.I. 1.409us-8870.400us Avg: 318.979us Max: 10687us
DALVIK THREADS (304):
"ReferenceQueueDaemon" daemon prio=5 tid=5 Waiting
    | group="system" sCount=1 ucsCount=0 flags=1 obj=0x12c02270 self=0xb400007ad4d07000
    | sysTid=2281 nice=4 cgrp=foreground sched=0/0 handle=0x7aeed48cb0
    | state=S schedstat=( 284481155 205167089 734 ) utm=6 stm=21 core=7 HZ=100
    | stack=0x7aeec45000-0x7aeec47000 stackSize=1039KB
    | held mutexes=
    at java.lang.Object.wait(Native method)
    - waiting on <0x037d6e4c> (a java.lang.Class<java.lang.ref.ReferenceQueue>)
    at java.lang.Object.wait(Object.java:386)
    at java.lang.Object.wait(Object.java:524)
    at java.lang.Daemons$ReferenceQueueDaemon.runInternal(Daemons.java:247)
    - locked <0x037d6e4c> (a java.lang.Class<java.lang.ref.ReferenceQueue>)
    at java.lang.Daemons$Daemon.run(Daemons.java:145)
    at java.lang.Thread.run(Thread.java:1012)

"FinalizerDaemon" daemon prio=5 tid=7 Waiting
    | group="system" sCount=1 ucsCount=0 flags=1 obj=0x12c02300 self=0xb400007ad4d08c00
    | sysTid=2282 nice=4 cgrp=foreground sched=0/0 handle=0x7a8dda9cb0
    | state=S schedstat=( 247375242 112008769 602 ) utm=10 stm=13 core=2 HZ=100
    | stack=0x7a8dca6000-0x7a8dca8000 stackSize=1039KB
    | held mutexes=
    at java.lang.Object.wait(Native method)
    - waiting on <0x0ecb4e95> (a java.lang.Object)
    at java.lang.Object.wait(Object.java:386)
    at java.lang.ref.ReferenceQueue.remove(ReferenceQueue.java:210)
    - locked <0x0ecb4e95> (a java.lang.Object)
    at java.lang.ref.ReferenceQueue.remove(ReferenceQueue.java:231)
    at java.lang.Daemons$FinalizerDaemon.runInternal(Daemons.java:317)
    at java.lang.Daemons$Daemon.run(Daemons.java:145)
    at java.lang.Thread.run(Thread.java:1012)

"""

    # Parse the process information
    # process_info = parse_process_info(thread_stack_content)
    # print("Process Info:")
    # print(process_info)
    # print("-" * 40)

    # # Parse the thread stack content
    # threads, waiting_threads, holding_threads = parse_threads(thread_stack_content)

    # # Display the lock contentions and thread details
    # display_thread_and_lock_info(
    #     process_info, threads, waiting_threads, holding_threads
    # )
