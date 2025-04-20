import unittest
from pathlib import Path

from python_bugreport_parser.bugreport.anr_record import AnrRecord, AnrProcess


class TestAnrRecord(unittest.TestCase):
    def test_anr_record(self):
        anr_record_path = Path("tests/data") / "example_anr_record"

        anr_record = AnrRecord()
        with open(anr_record_path, "r", encoding="utf-8") as f:
            anrfile_content = f.read()
            anr_record._split_anr_trace(anrfile_content)
            # print(anr_record.type)
            for trace in anr_record.traces:
                if trace.cmd_line == "system_server":
                    print(trace)
                    trace.display_thread_and_lock_info()


class TestAnrProcess(unittest.TestCase):
    def setUp(self):
        self.thread_stack_content = """----- pid 2270 at 2024-08-16 10:02:17.932278717+0700 -----
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

----- end 2270 -----

"""

    def test_anr_trace(self):
        anr_trace = AnrProcess.from_raw_str(self.thread_stack_content)
        print(str(anr_trace))
        anr_trace.display_thread_and_lock_info()
