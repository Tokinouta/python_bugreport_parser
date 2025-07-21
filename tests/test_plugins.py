import unittest
from datetime import datetime
from functools import reduce

from python_bugreport_parser.bugreport.section import LogcatLine
from python_bugreport_parser.plugins.input_focus_plugin import InputFocusPlugin
from python_bugreport_parser.plugins.invalid_bugreport_plugin import (
    InvalidBugreportPlugin,
)
from python_bugreport_parser.plugins.last_user_activity_plugin import (
    LastUserActivityPlugin,
)
from python_bugreport_parser.plugins.timestamp_plugin import TimestampPlugin

from .context import TEST_BUGREPORT_ANALYSIS_CONTEXT


# TODO: Add more tests with substantial content.

class TestTimestampPlugin(unittest.TestCase):
    def test_timestamp_plugin(self):
        plugin = TimestampPlugin()
        plugin.analyze(TEST_BUGREPORT_ANALYSIS_CONTEXT)

        expected = "2024-08-16T10:02:11"
        actual = plugin.report()

        # Check if the expected string is contained in the report
        self.assertIn(expected, actual)


class TestInputFocusPlugin(unittest.TestCase):
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
        plugin = InputFocusPlugin()
        self.event_log = next(
            (
                s
                for s in TEST_BUGREPORT_ANALYSIS_CONTEXT.bugreport.bugreport.bugreport_txt.sections
                if s.name == "EVENT LOG"
            ),
            None,
        )
        plugin.analyze(TEST_BUGREPORT_ANALYSIS_CONTEXT)
        results = plugin.report()

        for result in plugin.records:
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
    def test_invalid_bugreport_plugin(self):
        plugin = InvalidBugreportPlugin()
        plugin.analyze(TEST_BUGREPORT_ANALYSIS_CONTEXT)
        self.assertFalse(plugin.is_invalid)


class TestLastUserActivityPlugin(unittest.TestCase):
    def test_last_user_activity_plugin(self):
        plugin = LastUserActivityPlugin()
        plugin.analyze(TEST_BUGREPORT_ANALYSIS_CONTEXT)
        print(plugin.report())
