import unittest
from datetime import datetime, timedelta
from pathlib import Path

from python_bugreport_parser.bugreport import Metadata


class TestMetadataParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = Path("tests/data")
        cls.example_txt = cls.test_data_dir / "example.txt"

    def test_parse_timestamp(self):
        line = "== dumpstate: 2022-03-14 10:00:00"
        result = Metadata.parse_timestamp(line)
        expected = datetime(2022, 3, 14, 10, 0, 0)
        self.assertEqual(result, expected)

    def test_parse_version(self):
        line = "Build fingerprint: 'Xiaomi/haotian/haotian:15/AQ3A.240812.002/OS2.0.107.0.VOBCNXM:userdebug/test-keys'"
        version, product = Metadata.parse_version_and_product(line)
        self.assertEqual(version, "OS2.0.107.0.VOBCNXM")
        self.assertEqual(product, "haotian")

    def test_parse_uptime(self):
        line = "Uptime: up 0 weeks, 0 days, 1 hour, 59 minutes"
        result = Metadata.parse_uptime(line)
        expected = timedelta(hours=1, minutes=59)
        self.assertEqual(result.total_seconds(), expected.total_seconds())

    def test_full_parse(self):
        # Read test file
        with open(self.example_txt, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        metadata = Metadata()
        metadata.parse(iter(lines))

        # Test timestamp
        expected_time = datetime(2024, 8, 16, 10, 2, 11)
        self.assertEqual(metadata.timestamp, expected_time)

        # Test version
        self.assertEqual(metadata.version, "V816.0.12.0.UNCMIXM")

        # Test product
        self.assertEqual(metadata.product, "houji_global")

        # Test uptime (32 minutes)
        self.assertEqual(
            metadata.uptime.total_seconds(), timedelta(minutes=32).total_seconds()
        )

        # Test lines processed
        self.assertEqual(metadata.lines_passed, 50)
