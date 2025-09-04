import glob
import os
from pathlib import Path
from typing import List, Optional

from python_bugreport_parser.bugreport.anr_record import AnrRecord
from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt
from python_bugreport_parser.bugreport.dumpstate_board import DumpstateBoard
from python_bugreport_parser.bugreport.interfaces import LogFileInterface, LogLoadable
from python_bugreport_parser.utils import unzip_and_delete


class BugreportDirs:
    def __init__(self):
        self.bugreport_txt_path = Path()
        self.anr_files: List[Path] = []
        self.miuilog_reboot_dirs: List[Path] = []
        self.miuilog_scout_dirs: List[Path] = []
        self.dumpstate_board_path: Path = Path()
        self.mtdoops_md_path: Optional[Path] = None
        self.offline_log_path: Optional[Path] = None
        self.misight_path: Optional[Path] = None

    def __str__(self):
        return (
            f"BugreportDirs(bugreport_txt={self.bugreport_txt_path}, \n"
            f"anr_files={self.anr_files}, \n"
            f"miuilog_reboot_dir={self.miuilog_reboot_dirs}, \n"
            f"miuilog_scout_dir={self.miuilog_scout_dirs}), \n"
            f"dumpstate_board_path={self.dumpstate_board_path}, \n"
            f"mtdoops_md_path={self.mtdoops_md_path}, \n"
            f"offline_log_path={self.offline_log_path}, \n"
            f"misight_path={self.misight_path})"
        )

    def is_valid(self) -> bool:
        return self.bugreport_txt_path.exists() and self.dumpstate_board_path.exists()


class Bugreport(LogFileInterface, LogLoadable):
    """
    A class to parse and handle (zipped) bugreport.
    The bugreport is expected to be exported by `adb bugreport`.
    It extracts necessary files from a bug report zip, loads them into memory.
    """

    def __init__(self):
        self.bugreport_dirs: BugreportDirs = None
        self.bugreport_txt: BugreportTxt = None
        self.anr_records: List[AnrRecord] = []
        self.miuilog_reboots: List[str] = []
        self.miuilog_scouts: List[AnrRecord] = []
        self.dumpstate_board: DumpstateBoard = None

    @classmethod
    def from_zip(cls, zip_path: Path, feedback_dir: Path) -> Optional["Bugreport"]:
        try:
            unzip_and_delete(zip_path, feedback_dir)
            return Bugreport.from_dir(feedback_dir)
        except Exception as e:
            print(f"Error unzipping bugreport zip: {e}")
            return None

    @classmethod
    def from_dir(cls, feedback_dir: Path) -> Optional["Bugreport"]:
        bugreport = cls()
        try:
            bugreport.bugreport_dirs = Bugreport._load_required_file_paths(feedback_dir)
        except FileNotFoundError as e:
            print(e)
            return None
        bugreport.load()
        return bugreport

    def load(self):
        self.bugreport_txt = BugreportTxt(self.bugreport_dirs.bugreport_txt_path)
        self.bugreport_txt.load()
        for file in self.bugreport_dirs.anr_files:
            anr_record = AnrRecord()
            anr_record.load(file)
            self.anr_records.append(anr_record)
        self.miuilog_reboots = self.bugreport_dirs.miuilog_reboot_dirs
        for file in self.bugreport_dirs.miuilog_scout_dirs:
            anr_record = AnrRecord()
            anr_record.load(file)
            self.miuilog_scouts.append(anr_record)
        if self.bugreport_dirs.dumpstate_board_path:
            self.dumpstate_board = DumpstateBoard()
            self.dumpstate_board.load(self.bugreport_dirs.dumpstate_board_path)
        else:
            print("No dumpstate board file found")
        print("Loaded bugreport:", self)
        # print(len(self.anr_records), len(self.miuilog_reboots), len(self.miuilog_scouts))

    @staticmethod
    def _load_required_file_paths(bugreport_dir: Path) -> BugreportDirs:
        """Load the unzipped bugreport and gather some paths related to stability.

        Args:
            bugreport_dir (Path): Path to the unzipped bugreport.
        Returns:
            BugreportDirs: An object containing paths to the extracted directories.
        Raises:
            FileNotFoundError: If the bugreport.txt is not found.
        """
        bugreport_dirs = BugreportDirs()

        # Find bugreport txt file
        bugreport_txt_path = next(iter(glob.glob(str(bugreport_dir / "bugreport*.txt"))), None)
        if not bugreport_txt_path:
            print("No bugreport*.txt file found")
            raise FileNotFoundError("No bugreport*.txt file found")
        else:
            bugreport_dirs.bugreport_txt_path = Path(bugreport_txt_path)

        # Find dumpstate board file
        dumpstate_board_path = next(iter(glob.glob(str(bugreport_dir / "dumpstate_board*.txt"))), None)
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
        reboot_mqs_dir = bugreport_dir / "FS" / "data" / "miuilog" / "stability" / "reboot"

        if os.path.isdir(reboot_mqs_dir):
            # Unzip all zip files in this folder
            for zip_file in glob.glob(str(reboot_mqs_dir / "*.zip")):
                extract_dir = os.path.splitext(zip_file)[0]
                os.makedirs(extract_dir, exist_ok=True)
                try:
                    unzip_and_delete(Path(zip_file), Path(extract_dir))
                except Exception as e:
                    print(f"Error unzipping {zip_file}: {e}")
                else:
                    print(f"Unzipped {zip_file} to {extract_dir}")
                    bugreport_dirs.miuilog_reboot_dirs.append(Path(extract_dir))
        else:
            print("No reboot mqs folder found")

        # Find Scout files
        scout_mqs_dir = bugreport_dir / "FS" / "data" / "miuilog" / "stability" / "scout"
        if os.path.isdir(scout_mqs_dir):
            # Unzip all zip files in this folder
            if (scout_app_dir := scout_mqs_dir / "app") and os.path.isdir(scout_app_dir):
                for zip_file in os.listdir(scout_app_dir):
                    print(zip_file)
                    if os.path.isdir(scout_app_dir / zip_file):
                        bugreport_dirs.miuilog_scout_dirs.append(scout_app_dir / zip_file)
            if (scout_sys_dir := scout_mqs_dir / "sys") and os.path.isdir(scout_sys_dir):
                for zip_file in os.listdir(scout_sys_dir):
                    print(zip_file)
                    if os.path.isdir(scout_sys_dir / zip_file):
                        bugreport_dirs.miuilog_scout_dirs.append(scout_sys_dir / zip_file)
            if (scout_watchdog_dir := scout_mqs_dir / "watchdog") and os.path.isdir(scout_watchdog_dir):
                for zip_file in os.listdir(scout_watchdog_dir):
                    print(zip_file)
                    bugreport_dirs.miuilog_scout_dirs.append(scout_watchdog_dir / zip_file)
        else:
            print("No scout mqs folder found")

        print("Ready to return ", bugreport_dirs)
        return bugreport_dirs


class Log284(LogFileInterface, LogLoadable):
    """
    A class to handle log284 files.
    This is a zipped log file whose content is defined by an internal structure.
    It mainly contains the standard bugreport and mtdoops.md, which are essential for debugging.
    The log284 file is expected to be exported by secret code 284.
    """

    def __init__(self):
        self.bugreport_dirs: BugreportDirs = None
        self.bugreport: Bugreport = None
        self.mtdoops_md: str = ""
        self.offline_log: str = ""  # TODO: WE ALSO NEED TO ANALYSE OFFLINELOG
        self.misight: str = ""  # TODO: WE ALSO NEED TO UNZIP mishght.zip

    @classmethod
    def from_zip(cls, zip_path: Path, feedback_dir: Path) -> Optional["Log284"]:
        try:
            unzip_and_delete(zip_path, feedback_dir)
            return Log284.from_dir(feedback_dir)
        except Exception as e:
            print(f"Error unzipping 284 log: {e}")
            return None

    @classmethod
    def from_dir(cls, feedback_dir: Path) -> Optional["Log284"]:
        log284 = cls()

        try:
            bugreport_dirs = Log284._load_required_file_paths(feedback_dir)
        except FileNotFoundError as e:
            print(e)
            return None
        log284.bugreport_dirs = bugreport_dirs

        log284.bugreport = Bugreport()
        log284.bugreport.bugreport_dirs = bugreport_dirs
        log284.load()
        return log284

    def load(self) -> None:
        """
        Load the bugreport and mtdoops.md files.
        Args:
            bugreport_dirs (BugreportDirs): The directories containing the bugreport and mtdoops.md files.
        """
        self.bugreport.load()
        print(self.bugreport_dirs.mtdoops_md_path)
        # TODO: We need to change these paths to optionals, i.e. they may be None to represent nonexistant files
        if self.bugreport_dirs.mtdoops_md_path:
            with open(self.bugreport_dirs.mtdoops_md_path, "r", encoding="utf-8", errors="ignore") as f:
                self.mtdoops_md = f.read()
        if self.bugreport_dirs.offline_log_path:
            pass
            # with open(self.bugreport_dirs.offline_log_path, "r", encoding="utf-8", errors="ignore") as f:
            #     self.offline_log = f.read()
        if self.bugreport_dirs.misight_path:
            pass
            # with open(self.bugreport_dirs.misight_path, "r", encoding="utf-8", errors="ignore") as f:
            #     self.misight = f.read()

    @staticmethod
    def _load_required_file_paths(feedback_dir: Path) -> BugreportDirs:
        """
        Load the unzipped 284 log and gather some paths related to stability.
        Args:
            feedback_dir (Path): Path to the unzipped 284 log.
        Returns:
            BugreportDirs: An object containing paths to the extracted directories.
        Raises:
            FileNotFoundError: If the required files are not found, particularly the bugreport.txt file.
        """
        bugreport_dir = feedback_dir / "bugreport"
        print(bugreport_dir)

        # Unzip the bugreport if not extracted
        bugreport_zip_path = next(iter(glob.glob(str(feedback_dir / "bugreport*.zip"))), None)
        if not bugreport_zip_path:
            print("No bugreport*.zip file found")
        else:
            print(bugreport_dir, bugreport_zip_path)
            try:
                unzip_and_delete(Path(bugreport_zip_path), bugreport_dir)
            except Exception as e:
                raise e  # The bugreport may be corrupted

        try:
            paths = Bugreport._load_required_file_paths(bugreport_dir)
        except FileNotFoundError as e:
            raise e

        # The files below are optional, so their default values are None, and will be set to an actual path
        # only when the file exists.
        if (mtdoops_md_path := feedback_dir / "mtdoops.md") and mtdoops_md_path.exists():
            paths.mtdoops_md_path = mtdoops_md_path
        else:
            print("No mtdoops.md file found")

        if (offline_log_path := feedback_dir / "offlinelog") and offline_log_path.exists():
            paths.offline_log_path = offline_log_path
        elif (offline_log_path := feedback_dir / "log") and offline_log_path.exists():
            paths.offline_log_path = offline_log_path
        else:
            print("No offline.log file found")

        if (misight_zip_path := feedback_dir / "misight.zip") and misight_zip_path.exists():
            paths.misight_path = feedback_dir / "misight"
            try:
                unzip_and_delete(misight_zip_path, paths.misight_path)
            except Exception as e:
                print(f"Error unzipping misight.zip: {e}")
        else:
            print("No misight.zip file found")

        return paths
