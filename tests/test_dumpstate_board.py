import unittest
from pathlib import Path
from python_bugreport_parser.bugreport.dumpstate_board import DumpstateBoard


class TestDumpstateBoard(unittest.TestCase):
    def test_load_valid_file(self):
        # Create a dummy dumpstate_board.txt file for testing
        test_file_content = """------ SECTION 1 (time)
Content of section 1
------ SECTION 2 (time)
Content of section 2
        """
        test_file_path = Path("test_dumpstate_board.txt")
        with open(test_file_path, "w") as f:
            f.write(test_file_content)

        dumpstate_board = DumpstateBoard()
        dumpstate_board.load(test_file_path)

        self.assertEqual(len(dumpstate_board.sections), 2)
        self.assertEqual(dumpstate_board.sections[0][0], "SECTION 1")
        self.assertEqual(
            "".join(dumpstate_board.sections[0][1]).strip(),
            "Content of section 1",
        )
        self.assertEqual(dumpstate_board.sections[1][0], "SECTION 2")
        self.assertEqual(
            "".join(dumpstate_board.sections[1][1]).strip(),
            "Content of section 2",
        )

        # Clean up the dummy file
        test_file_path.unlink()

    def test_load_empty_file(self):
        # Create an empty dumpstate_board.txt file
        test_file_path = Path("test_dumpstate_board.txt")
        with open(test_file_path, "w") as f:
            pass

        dumpstate_board = DumpstateBoard()
        dumpstate_board.load(test_file_path)

        self.assertEqual(len(dumpstate_board.sections), 0)

        # Clean up the dummy file
        test_file_path.unlink()

    def test_load_file_with_no_sections(self):
        # Create a dumpstate_board.txt file with no sections
        test_file_content = "This is a file with no sections."
        test_file_path = Path("test_dumpstate_board.txt")
        with open(test_file_path, "w") as f:
            f.write(test_file_content)

        dumpstate_board = DumpstateBoard()
        dumpstate_board.load(test_file_path)

        self.assertEqual(len(dumpstate_board.sections), 1)
        self.assertEqual(dumpstate_board.sections[0][0], None)
        self.assertEqual(
            "".join(dumpstate_board.sections[0][1]).strip(),
            "This is a file with no sections.",
        )

        # Clean up the dummy file
        test_file_path.unlink()

    def test_load_file_with_empty_sections(self):
        # Create a dumpstate_board.txt file with empty sections
        test_file_content = """------ SECTION 1 (time)

------ SECTION 2 (time)
"""
        test_file_path = Path("test_dumpstate_board.txt")
        with open(test_file_path, "w") as f:
            f.write(test_file_content)

        dumpstate_board = DumpstateBoard()
        dumpstate_board.load(test_file_path)
        print(dumpstate_board.sections)

        self.assertEqual(len(dumpstate_board.sections), 2)
        self.assertEqual(dumpstate_board.sections[0][0], "SECTION 1")
        self.assertEqual(len(dumpstate_board.sections[0][1]), 1)
        self.assertEqual(dumpstate_board.sections[1][0], "SECTION 2")
        self.assertEqual(len(dumpstate_board.sections[1][1]), 0)

        # Clean up the dummy file
        test_file_path.unlink()

    def test_load_realworld_file(self):
        # This test requires a real dumpstate_board.txt file to be present.
        # You can replace the path with a valid one for your testing.
        real_file_path = Path("tests/data/dumpstate_board.txt")
        dumpstate_board = DumpstateBoard()
        dumpstate_board.load(real_file_path)

        # Add assertions based on the expected content of the real file
        self.assertTrue(dumpstate_board.sections)
        print([dumpstate_board.sections[i][0] for i in range(len(dumpstate_board.sections))])
