import glob
import os
from pathlib import Path
from typing import List
import zipfile
import tomllib  # or import tomli as tomllib for older versions

from python_bugreport_parser.bugreport.anr_record import AnrRecord
from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt
from python_bugreport_parser.bugreport.dumpstate_board import DumpstateBoard


CONFIG_PATH = Path(__file__).parent.parent.parent / "config/config.toml"
with open(CONFIG_PATH, "rb") as f:
    config = tomllib.load(f)
extract_path = Path(config["extract_path"])


def unzip_and_delete(zip_file: Path, unzip_dir: Path):
    os.makedirs(unzip_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(unzip_dir)
        os.remove(zip_file)
    except (zipfile.BadZipFile, PermissionError, FileNotFoundError) as e:
        print(f"Error processing {zip_file}: {e}")


# def extract(unzip_dir: Path, zip_file: Path) -> None:
#     os.makedirs(unzip_dir, exist_ok=True)
#     unzip_and_delete(zip_file, unzip_dir)


class BugreportDirs:
    def __init__(self):
        self.bugreport_txt_path = Path()
        self.anr_files: List[Path] = []
        self.miuilog_reboot_dirs: List[Path] = []
        self.miuilog_scout_dirs: List[Path] = []
        self.dumpstate_board_path: Path = Path()

    def __str__(self):
        return (
            f"BugreportDirs(bugreport_txt={self.bugreport_txt_path}, \n"
            f"anr_files={self.anr_files}, \n"
            f"miuilog_reboot_dir={self.miuilog_reboot_dirs}, \n"
            f"miuilog_scout_dir={self.miuilog_scout_dirs})"
        )


class Bugreport:
    """
    A class to parse and handle (zipped) bugreport.
    The bugreport is expected to be exported by `adb bugreport`.
    It extracts necessary files from a bug report zip, loads them into memory.
    """

    def __init__(self):
        self.bugreport_txt: BugreportTxt = None
        self.anr_records: List[AnrRecord] = []
        self.miuilog_reboots: List[str] = []
        self.miuilog_scouts: List[AnrRecord] = []
        self.dumpstate_board: DumpstateBoard = None

    @classmethod
    def from_zip(cls, bugreport_zip_path: Path, feedback_id: str) -> "Bugreport":
        feedback_dir = extract_path / str(feedback_id)
        unzip_and_delete(
            zip_file=bugreport_zip_path,
            unzip_dir=feedback_dir,
        )
        return Bugreport.from_dir(feedback_dir)

    @classmethod
    def from_dir(cls, feedback_dir: Path) -> "Bugreport":
        bugreport = cls()
        bugreport_dirs = Bugreport.load_required_file_paths(feedback_dir)
        bugreport.load(bugreport_dirs)
        return bugreport

    @staticmethod
    def load_required_file_paths(bugreport_dir: Path) -> BugreportDirs:
        """
        Load the unzipped bugreport and gather some paths related to stability.
        Args:
            feedback_dir (Path): Path to the unzipped bugreport.
        Returns:
            BugreportDirs: An object containing paths to the extracted directories.
        """
        bugreport_dirs = BugreportDirs()

        # Find bugreport txt file
        bugreport_txt_path = next(
            iter(glob.glob(str(bugreport_dir / "bugreport*.txt"))), None
        )
        if not bugreport_txt_path:
            print("No bugreport*.txt file found")
            return None
        else:
            bugreport_txt_path = Path(bugreport_txt_path)
            bugreport_dirs.bugreport_txt_path = bugreport_txt_path

        # Find dumpstate board file
        dumpstate_board_path = next(
            iter(glob.glob(str(bugreport_dir / "dumpstate_board*.txt"))), None
        )
        if dumpstate_board_path:
            bugreport_dirs.dumpstate_board_path = Path(dumpstate_board_path)

        # Find ANR files
        anr_files_dir = bugreport_dir / "FS" / "data" / "anr"
        if os.path.isdir(anr_files_dir):
            for file in os.listdir(anr_files_dir):
                print(file)
                bugreport_dirs.anr_files.append(anr_files_dir / file)
        else:
            print("No anr folder found")

        # Find MQS reboot files
        reboot_mqs_dir = (
            bugreport_dir / "FS" / "data" / "miuilog" / "stability" / "reboot"
        )

        if os.path.isdir(reboot_mqs_dir):
            # Unzip all zip files in this folder
            for zip_file in glob.glob(str(reboot_mqs_dir / "*.zip")):
                print(zip_file)
                extract_dir = os.path.splitext(zip_file)[0]
                os.makedirs(extract_dir, exist_ok=True)
                unzip_and_delete(zip_file, extract_dir)
                print(f"Unzipped {zip_file} to {extract_dir}")
                bugreport_dirs.miuilog_reboot_dirs.append(Path(extract_dir))
        else:
            print("No reboot mqs folder found")

        # Find Scout files
        scout_mqs_dir = (
            bugreport_dir / "FS" / "data" / "miuilog" / "stability" / "scout"
        )
        if os.path.isdir(scout_mqs_dir):
            # Unzip all zip files in this folder
            if (scout_app_dir := scout_mqs_dir / "app") and os.path.isdir(
                scout_app_dir
            ):
                for zip_file in os.listdir(scout_app_dir):
                    print(zip_file)
                    if os.path.isdir(scout_app_dir / zip_file):
                        bugreport_dirs.miuilog_scout_dirs.append(
                            scout_app_dir / zip_file
                        )
            if (scout_sys_dir := scout_mqs_dir / "sys") and os.path.isdir(
                scout_sys_dir
            ):
                for zip_file in os.listdir(scout_sys_dir):
                    print(zip_file)
                    if os.path.isdir(scout_sys_dir / zip_file):
                        bugreport_dirs.miuilog_scout_dirs.append(
                            scout_sys_dir / zip_file
                        )
            if (scout_watchdog_dir := scout_mqs_dir / "watchdog") and os.path.isdir(
                scout_watchdog_dir
            ):
                for zip_file in os.listdir(scout_watchdog_dir):
                    print(zip_file)
                    bugreport_dirs.miuilog_scout_dirs.append(
                        scout_watchdog_dir / zip_file
                    )
        else:
            print("No scout mqs folder found")

        print("Ready to return ", bugreport_dirs)
        return bugreport_dirs

    def load(self, bugreport_dirs: BugreportDirs):
        self.bugreport_txt = BugreportTxt(bugreport_dirs.bugreport_txt_path)
        self.bugreport_txt.load()
        for file in bugreport_dirs.anr_files:
            anr_record = AnrRecord()
            anr_record.load(file)
            self.anr_records.append(anr_record)
        self.miuilog_reboots = bugreport_dirs.miuilog_reboot_dirs
        for file in bugreport_dirs.miuilog_scout_dirs:
            anr_record = AnrRecord()
            anr_record.load(file)
            self.miuilog_scouts.append(anr_record)
        if bugreport_dirs.dumpstate_board_path:
            self.dumpstate_board = DumpstateBoard()
            self.dumpstate_board.load(bugreport_dirs.dumpstate_board_path)
        else:
            print("No dumpstate board file found")
        print("Loaded bugreport:", self)
        # print(len(self.anr_records), len(self.miuilog_reboots), len(self.miuilog_scouts))


class Log284:
    """
    A class to handle log284 files.
    This is a zipped log file whose content is defined by an internal structure.
    It mainly contains the standard bugreport and mtdoops.md, which are essential for debugging.
    The log284 file is expected to be exported by secret code 284.
    """

    def __init__(self):
        self.bugreport: Bugreport = None
        self.mtdoops_md: str = ""

    @classmethod
    def from_zip(cls, log284_zip_path: Path, feedback_id: str) -> "Log284":
        feedback_dir = extract_path / str(feedback_id)
        unzip_and_delete(
            unzip_dir=feedback_dir,
            zip_file=log284_zip_path,
        )
        return Log284.from_dir(feedback_dir)

    @classmethod
    def from_dir(cls, feedback_dir: Path) -> "Log284":
        log284 = cls()
        bugreport_dirs = Log284.load_required_file_paths(feedback_dir)
        log284.bugreport = Bugreport()
        log284.bugreport.load(bugreport_dirs)
        mtdoops_md_path = feedback_dir / "mtdoops.md"
        if mtdoops_md_path.exists():
            with open(mtdoops_md_path, "r") as f:
                log284.mtdoops_md = f.read()
        return log284

    @staticmethod
    def load_required_file_paths(feedback_dir: Path) -> BugreportDirs:
        """
        Load the unzipped 284 log and gather some paths related to stability.
        Args:
            feedback_dir (Path): Path to the unzipped 284 log.
        Returns:
            BugreportDirs: An object containing paths to the extracted directories.
        """
        bugreport_dir = feedback_dir / "bugreport"
        print(bugreport_dir)

        # Unzip the bugreport if not extracted
        bugreport_zip_path = next(
            iter(glob.glob(str(feedback_dir / "bugreport*.zip"))), None
        )
        if not bugreport_zip_path:
            print("No bugreport*.zip file found")
        else:
            print(bugreport_dir, bugreport_zip_path)
            unzip_and_delete(zip_file=bugreport_zip_path, unzip_dir=bugreport_dir)

        return Bugreport.load_required_file_paths(bugreport_dir)
