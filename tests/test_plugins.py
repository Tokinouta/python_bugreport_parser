import unittest
import zipfile
from datetime import datetime
from pathlib import Path

from python_bugreport_parser.bugreport.section import LogcatLine
from python_bugreport_parser.plugins.input_focus_plugin import (
    InputFocusPlugin,
)
from python_bugreport_parser.plugins.last_user_activity_plugin import (
    LastUserActivityPlugin,
)
from python_bugreport_parser.plugins.timestamp_plugin import TimestampPlugin
from python_bugreport_parser.plugins.invalid_bugreport_plugin import (
    InvalidBugreportPlugin,
)

from .context import TEST_BUGREPORT_TXT
from functools import reduce


class TestTimestampPlugin(unittest.TestCase):
    def setUp(self):
        # Setup similar to Rust's test_setup_bugreport
        self.bugreport = TEST_BUGREPORT_TXT

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

        self.bugreport = TEST_BUGREPORT_TXT

        self.plugin = InputFocusPlugin()

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
        results = self.plugin.report()

        for result in self.plugin.records:
            print(result)
            events = []
            if result.request is not None:
                events.append(result.request)
            if result.receive is not None:
                events.append(result.receive)
            if result.entering is not None:
                events.append(result.entering)
            if result.leaving is not None:
                events.append(result.leaving)
            # Check if all events have the same focus_id
            focus_ids = {event.focus_id for event in events}
            self.assertEqual(
                len(focus_ids), 1, "All events should have the same focus_id"
            )
            # Check if the timestamps are in the correct order
            timestamps = [event.timestamp for event in events]
            self.assertTrue(
                reduce(
                    lambda x, y: x and y[0] <= y[1],
                    zip(timestamps, timestamps[1:]),
                    True,
                ),
                "Timestamps are not in the correct order",
            )


class TestInvalidBugreportPlugin(unittest.TestCase):
    def setUp(self):
        self.bugreport = TEST_BUGREPORT_TXT
        self.plugin = InvalidBugreportPlugin()

    def test_invalid_bugreport_plugin(self):
        # Simulate an invalid bugreport
        self.plugin.analyze(self.bugreport)

        # Check if the plugin correctly identifies the invalid bugreport
        self.assertFalse(self.plugin.is_invalid)


class TestLastUserActivityPlugin(unittest.TestCase):
    def setUp(self):
        self.bugreport = TEST_BUGREPORT_TXT
        self.plugin = LastUserActivityPlugin()

    def test_last_user_activity_plugin(self):
        # Simulate an invalid bugreport
        # self.bugreport.metadata.timestamp = None
        self.plugin.analyze(self.bugreport)

        # Check if the plugin correctly identifies the invalid bugreport
        print(self.plugin.report())
