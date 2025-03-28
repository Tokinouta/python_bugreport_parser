from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import Mock
import zipfile

from .context import python_bugreport_parser
from python_bugreport_parser.bugreport.section import LogcatLine, Section
from python_bugreport_parser.bugreport import BugreportTxt
from python_bugreport_parser.plugins.timestamp_plugin import TimestampPlugin
from python_bugreport_parser.plugins.input_focus_plugin import (
    InputFocusPlugin,
    INPUT_FOCUS_REQUEST,
)


class TestTimestampPlugin(unittest.TestCase):
    def setUp(self):
        # Setup similar to Rust's test_setup_bugreport
        self.bugreport = BugreportTxt("tests/data/example.txt")
        self.bugreport.load()

    def test_timestamp_plugin(self):
        plugin = TimestampPlugin()
        plugin.analyze(self.bugreport)

        # Expected format: "2024-08-16T10:02:11+08:00"
        expected = "2024-08-16T10:02:11"
        actual = plugin.report()

        # Check if the expected string is contained in the report
        self.assertIn(expected, actual)


class TestInputFocusPlugin(unittest.TestCase):
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
        self.bugreport.load()

        self.plugin = InputFocusPlugin()
        # self.mock_section = Mock(spec=Section)
        # self.mock_section.name = "EVENT LOG"

        # # Setup test log lines
        # self.logs = [
        #     self._create_log_line("Focus request com.example.Activity,reason=TOUCH"),
        #     self._create_log_line("Focus receive :com.example.Activity"),
        #     self._create_log_line("Focus entering com.example.Activity"),
        #     self._create_log_line("Focus leaving com.example.Activity"),
        # ]

    def _create_log_line(self, message: str) -> LogcatLine:
        return LogcatLine(
            timestamp=datetime.now(),
            user="system",
            pid=1000,
            tid=2000,
            level="D",
            tag="input_focus",
            message=message,
        )

    def test_pair_input_focus(self):
        self.event_log = next(
            (s for s in self.bugreport.sections if s.name == "EVENT LOG"), None
        )
        self.plugin.analyze(self.bugreport)
        results = self.plugin.records

        for result in results:
            match = INPUT_FOCUS_REQUEST.search(result.request.message)
            request_activity = match.group(1)
            self.assertIsNotNone(request_activity)

            if result.receive is None:
                continue
            self.assertIn(request_activity, result.receive.message)
            self.assertGreaterEqual(result.receive.timestamp, result.request.timestamp)

            if result.entering is None:
                continue
            self.assertIn(request_activity, result.entering.message)
            self.assertGreaterEqual(result.entering.timestamp, result.receive.timestamp)

            if result.leaving is None:
                continue
            self.assertIn(request_activity, result.leaving.message)
            # self.assertGreaterEqual(result.leaving.timestamp, result.entering.timestamp)
