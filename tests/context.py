import zipfile
from datetime import datetime
from pathlib import Path

from python_bugreport_parser.bugreport import BugreportTxt, dumpsys_entry
from python_bugreport_parser.bugreport.bugreport_all import Bugreport
from python_bugreport_parser.plugins import BugreportAnalysisContext

dumpsys_entry.REBOOT_RECORD_START = (
    "---------- kernel abnormal reboot records ----------"
)


# Setup that runs once before all tests
def setup_bugreport_txt():
    test_data_dir = Path("tests/data")
    example_txt = test_data_dir / "example.txt"
    example_zip = test_data_dir / "example.zip"

    # Runs before each test
    if not example_txt.exists():
        print(f"File '{example_txt}' does not exist. Extracting from ZIP...")

        with zipfile.ZipFile(example_zip, "r") as zip_ref:
            zip_ref.extractall(test_data_dir)

        print("Extraction complete.")

    bugreport = BugreportTxt(example_txt)
    bugreport.load()
    bugreport.set_error_timestamp(datetime(2024, 7, 28, 13, 15, 0))
    return bugreport


TEST_BUGREPORT_TXT = setup_bugreport_txt()
TEST_BUGREPORT_ANALYSIS_CONTEXT = BugreportAnalysisContext()
TEST_BUGREPORT_ANALYSIS_CONTEXT.bugreport = Bugreport()
TEST_BUGREPORT_ANALYSIS_CONTEXT.bugreport.bugreport_txt = TEST_BUGREPORT_TXT
