import unittest
from datetime import datetime
from python_bugreport_parser.bugreport import (
    LogcatSection,
    LogcatLine,
)
from python_bugreport_parser.bugreport.dumpsys_entry import (
    MqsServiceDumpsysEntry,
)
from .context import TEST_BUGREPORT_TXT


class TestMqsServiceDumpsysEntry(unittest.TestCase):
    def setUp(self):
        self.bugreport = TEST_BUGREPORT_TXT

    def test_parse_line(self):
        dumpsys = next(
            (s for s in self.bugreport.sections if s.name == "DUMPSYS"), None
        )

        # for entry in dumpsys.content.entries:
        #     print(entry.name)

        mqs_dumpsys: MqsServiceDumpsysEntry = next(
            (s for s in dumpsys.content.entries if s.name == "miui.mqsas.MQSService"),
            None,
        )

        results = mqs_dumpsys.boot_records
        self.assertEqual(len(results), 48)

        # Verify all results have correct level
        for entry in results:
            print(entry)
            # self.assertEqual(entry.level, "D")
