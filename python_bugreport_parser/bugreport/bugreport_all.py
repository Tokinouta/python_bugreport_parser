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
    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(unzip_dir)
        os.remove(zip_file)
    except (zipfile.BadZipFile, PermissionError, FileNotFoundError) as e:
        print(f"Error processing {zip_file}: {e}")


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
    def __init__(self):
        self.bugreport_txt: BugreportTxt = None
        self.anr_records: List[AnrRecord] = []
        self.miuilog_reboots: List[str] = []
        self.miuilog_scouts: List[AnrRecord] = []
        self.dumpstate_board: DumpstateBoard = None

    @classmethod
    def from_zip(cls, bugreport_zip_path: Path, feedback_id: str) -> "Bugreport":
        bugreport = cls()
        feedback_dir = extract_path / str(feedback_id)
        Bugreport.extract(
            feedback_dir=feedback_dir,
            bugreport_zip_path=bugreport_zip_path,
        )
        bugreport_dirs = Bugreport.load_required_file_paths(feedback_dir)
        bugreport.load(bugreport_dirs)
        return bugreport

    @classmethod
    def from_dir(cls, feedback_id: str) -> "Bugreport":
        bugreport = cls()
        feedback_dir = extract_path / str(feedback_id)
        bugreport_dirs = Bugreport.load_required_file_paths(feedback_dir)
        bugreport.load(bugreport_dirs)
        return bugreport

    @staticmethod
    def extract(feedback_dir: Path, bugreport_zip_path: Path) -> None:
        os.makedirs(feedback_dir, exist_ok=True)
        unzip_and_delete(bugreport_zip_path, feedback_dir)

    @staticmethod
    def load_required_file_paths(feedback_dir: Path) -> BugreportDirs:
        """
        Load the unzipped bugreport and gather some paths related to stability.
        Args:
            feedback_dir (Path): Path to the unzipped bugreport.
        Returns:
            BugreportDirs: An object containing paths to the extracted directories.
        """

        bugreport_dirs = BugreportDirs()
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
            os.makedirs(bugreport_dir, exist_ok=True)
            unzip_and_delete(bugreport_zip_path, bugreport_dir)

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
                        bugreport_dirs.miuilog_scout_dirs.append(scout_app_dir / zip_file)
            if (scout_sys_dir := scout_mqs_dir / "sys") and os.path.isdir(
                scout_sys_dir
            ):
                for zip_file in os.listdir(scout_sys_dir):
                    print(zip_file)
                    if os.path.isdir(scout_sys_dir / zip_file):
                        bugreport_dirs.miuilog_scout_dirs.append(scout_sys_dir / zip_file)
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
