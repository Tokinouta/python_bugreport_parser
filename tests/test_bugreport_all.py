import unittest
from pathlib import Path

from python_bugreport_parser.bugreport import Bugreport


class TestBugreportAll(unittest.TestCase):
    def test_extract(self):
        """
        This test depends on the existence of a specific bugreport zip file.
        Need to update the path and feedback_id accordingly.
        """
        bugreport_zip_path = Path(
            "/home/dayong/Downloads/2025-03-18-102835-223309632.zip"
        )
        feedback_id = Path("111353833")

        bugreport = Bugreport.from_zip(bugreport_zip_path, feedback_id)
        self.assertTrue(bugreport.bugreport_txt.loaded)
