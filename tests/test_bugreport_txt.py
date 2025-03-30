import time
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

# Actually, this was introduced from a blog, but it seems to have no effect
# keep it commented out in case it becomes necessary
# from .context import python_bugreport_parser
from python_bugreport_parser.bugreport import (
    BugreportTxt,
    DumpsysSection,
    LogcatSection,
    OtherSection,
    SystemPropertySection,
)


class TestBugreport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup that runs once before all tests
        cls.test_data_dir = Path("tests/data")
        cls.example_txt = cls.test_data_dir / "example.txt"
        cls.example_zip = cls.test_data_dir / "example.zip"

    def setUp(self):
        # Runs before each test
        if not self.example_txt.exists():
            print(f"File '{self.example_txt}' does not exist. Extracting from ZIP...")

            with zipfile.ZipFile(self.example_zip, "r") as zip_ref:
                zip_ref.extractall(self.test_data_dir)

            print("Extraction complete.")

        self.bugreport = BugreportTxt(self.example_txt)

    def test_read_and_slice(self):
        matches = self.bugreport.read_and_slice()
        self.assertEqual(len(matches), 274)

        # Test timestamp
        expected_date = datetime(2024, 8, 16, 10, 2, 11)
        self.assertEqual(self.bugreport.metadata.timestamp, expected_date)

    def test_pair_sections(self):
        start_time = time.time()
        matches = self.bugreport.read_and_slice()
        parse_time = time.time() - start_time
        print(f"Time taken for read_and_slice: {parse_time:.2f}s")

        start_time = time.time()
        self.bugreport.pair_sections(matches)
        pair_time = time.time() - start_time
        print(f"Time taken for pair_sections: {pair_time:.2f}s")

        # There are still invalid sections, but just ignore them for now
        # They won't cause issues in our analysis
        self.assertEqual(len(self.bugreport.sections), 114)

        # Find sections by type
        system_log = next(
            (s for s in self.bugreport.sections if s.name == "SYSTEM LOG"), None
        )
        self.assertIsInstance(system_log.content, LogcatSection)

        event_log = next(
            (s for s in self.bugreport.sections if s.name == "EVENT LOG"), None
        )
        self.assertIsInstance(event_log.content, LogcatSection)

        dumpsys = next(
            (s for s in self.bugreport.sections if s.name == "DUMPSYS"), None
        )
        self.assertIsInstance(dumpsys.content, DumpsysSection)

        system_props = next(
            s for s in self.bugreport.sections if s.name == "SYSTEM PROPERTIES"
        )
        self.assertIsInstance(system_props.content, SystemPropertySection)

        other = next(
            (
                s
                for s in self.bugreport.sections
                if s.name not in {"SYSTEM LOG", "EVENT LOG", "DUMPSYS"}
            ),
            None,
        )
        self.assertIsInstance(other.content, OtherSection)

    def test_parse_line(self):
        matches = self.bugreport.read_and_slice()
        self.bugreport.pair_sections(matches)

        system_log_sections = [
            s for s in self.bugreport.sections if s.name == "SYSTEM LOG"
        ]

        # Test first SYSTEM LOG section
        first_syslog = system_log_sections[0]
        self.assertEqual(
            len(first_syslog.content.entries),
            first_syslog.end_line - first_syslog.start_line + 1 - 7,
        )

        # Test second SYSTEM LOG section
        if len(system_log_sections) > 1:
            second_syslog = system_log_sections[1]
            self.assertEqual(
                len(second_syslog.content.entries),
                second_syslog.end_line - second_syslog.start_line + 1 - 2,
            )

        # Test EVENT LOG section
        event_log = next(s for s in self.bugreport.sections if s.name == "EVENT LOG")
        self.assertEqual(
            len(event_log.content.entries),
            event_log.end_line - event_log.start_line + 1 - 1,
        )

        # Test SYSTEM PROPERTIES section
        system_props = next(
            s for s in self.bugreport.sections if s.name == "SYSTEM PROPERTIES"
        )
        print(system_props.start_line, system_props.end_line)
        self.assertEqual(
            system_props.content.properties["persist.sys.boot.reason.history"],
            "reboot,1723775375\nreboot,1723774219\nreboot,1723648846\nreboot,1723598091",
        )
        # The above property costs 3 extra lines, so minus 3 here
        self.assertEqual(
            len(system_props.content.properties), system_props.get_line_numbers() - 3
        )
