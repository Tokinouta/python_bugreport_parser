import unittest
from datetime import datetime
from .context import python_bugreport_parser
from python_bugreport_parser.bugreport import (
    LogcatSection,
    LogcatLine,
)


class TestLogcatSection(unittest.TestCase):
    def setUp(self):
        self.test_lines = """
08-16 10:01:30.003  1000  5098  5850 D LocalBluetoothAdapter: isSupportBluetoothRestrict = 0
08-16 10:01:31.003 10160  5140  5140 D RecentsImpl: hideNavStubView
08-16 10:01:32.003 10160  5140  5140 D NavStubView_Touch: setKeepHidden    old=false   new=true
08-16 10:01:33.003 10160  5140  5300 D GestureStubView_Touch: setKeepHidden    old=false   new=false
08-16 10:01:34.003  1000  2270  5305 D PerfShielderService: com.android.systemui|StatusBar|171|1389485333739|171|0|1
08-16 10:01:35.003 10160  5140  5300 W GestureStubView: adaptRotation   currentRotation=0   mRotation=0
08-16 10:01:36.003 10160  5140  5300 D GestureStubView: resetRenderProperty: showGestureStub   isLayoutParamChanged=false
08-16 10:01:37.003 10160  5140  5300 D GestureStubView_Touch: disableTouch    old=false   new=false
08-16 10:01:38.003 10160  5140  5300 D GestureStubView: showGestureStub
08-16 10:01:39.003 10160  5140  5300 D GestureStubView_Touch: setKeepHidden    old=false   new=false
""".strip().split(
            "\n"
        )

        self.section = LogcatSection()
        self.section.parse(self.test_lines, 2024)

    def test_logcat_line_formatting(self):
        timestamp = datetime(2024, 8, 16, 10, 2, 11)
        log_line = LogcatLine(
            timestamp=timestamp,
            user="user",
            pid=1234,
            tid=5678,
            level="I",
            tag="tag",
            message="message",
        )

        expected = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')} user 1234 5678 I tag: message"
        self.assertEqual(str(log_line), expected)

    def test_search_by_tag(self):
        results = self.section.search_by_tag("GestureStubView")
        self.assertEqual(len(results), 3)

        # Verify all results have correct tag
        for entry in results:
            self.assertEqual(entry.tag, "GestureStubView")

    def test_search_by_time(self):
        target_time = datetime(2024, 8, 16, 10, 1, 34)
        results = self.section.search_by_time(target_time)
        self.assertEqual(len(results), 2)

        # Verify timestamps are within 1 second
        for entry in results:
            time_diff = abs(entry.timestamp - target_time).total_seconds()
            self.assertLessEqual(time_diff, 1)

    def test_search_by_level(self):
        results = self.section.search_by_level("D")
        self.assertEqual(len(results), 9)

        # Verify all results have correct level
        for entry in results:
            self.assertEqual(entry.level, "D")
