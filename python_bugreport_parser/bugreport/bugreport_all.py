import glob
import os
from pathlib import Path
from typing import List
import zipfile
import tomllib  # or import tomli as tomllib for older versions

from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt


CONFIG_PATH = Path(__file__).parent.parent.parent / "config/config.toml"
with open(CONFIG_PATH, "rb") as f:
    config = tomllib.load(f)
extract_path = Path(config["extract_path"])


class BugreportDirs:
    def __init__(self):
        self.bugreport_txt = Path()
        self.anr_files: List[Path] = []
        self.miuilog_reboot_dirs: List[Path] = []
        self.miuilog_scout_dirs: List[Path] = []

    def __str__(self):
        return (
            f"BugreportDirs(bugreport_txt={self.bugreport_txt}, \n"
            f"anr_files={self.anr_files}, \n"
            f"miuilog_reboot_dir={self.miuilog_reboot_dirs}, \n"
            f"miuilog_scout_dir={self.miuilog_scout_dirs})"
        )


class Bugreport:
    def __init__(self):
        self.bugreport_txt: BugreportTxt = None
        self.anr_files: List[str] = []
        self.miuilog_reboots: List[str] = []
        self.miuilog_scouts: List[str] = []

    @classmethod
    def from_zip(cls, bugreport_zip_path: Path, feedback_id: str) -> "Bugreport":
        bugreport = cls()
        bugreport_dirs = Bugreport.extract(
            feedback_id=feedback_id,
            bugreport_zip_path=bugreport_zip_path,
            bugreport_extract_path=extract_path,
        )
        bugreport.bugreport_txt = BugreportTxt(bugreport_dirs.bugreport_txt)
        bugreport.bugreport_txt.load()
        bugreport.anr_files = bugreport_dirs.anr_files
        bugreport.miuilog_reboots = bugreport_dirs.miuilog_reboot_dirs
        bugreport.miuilog_scouts = bugreport_dirs.miuilog_scout_dirs
        return bugreport

    @classmethod
    def extract(
        cls, feedback_id, bugreport_zip_path: Path, bugreport_extract_path: Path
    ) -> BugreportDirs:
        """
        Extracts the bugreport zip file and organizes its contents into directories.
        Args:
            feedback_id (str): The feedback ID.
            bugreport_zip (Path): Path to the bugreport zip file.
            user_feedback_path (Path): Path to the user feedback directory.
        Returns:
            BugreportDirs: An object containing paths to the extracted directories.
        """
        bugreport_dirs = BugreportDirs()

        def unzip_and_delete(zip_file: Path, unzip_dir: Path):
            try:
                with zipfile.ZipFile(zip_file, "r") as zip_ref:
                    zip_ref.extractall(unzip_dir)
                os.remove(zip_file)
            except (zipfile.BadZipFile, PermissionError, FileNotFoundError) as e:
                print(f"Error processing {zip_file}: {e}")

        # Create feedback directory if it doesn't exist
        feedback_dir = bugreport_extract_path / str(feedback_id)
        os.makedirs(feedback_dir, exist_ok=True)

        # Extract and remove the initial bugreport zip
        unzip_and_delete(bugreport_zip_path, feedback_dir)

        # Change to feedback directory
        # os.chdir(feedback_dir)

        # Find bugreport zip file
        bugreport_zip_path = next(
            iter(glob.glob(str(feedback_dir / "bugreport*.zip"))), None
        )
        if not bugreport_zip_path:
            print("No bugreport*.zip file found")
            return

        # Create directory name from zip filename
        bugreport_dir = feedback_dir / "bugreport"
        print(bugreport_dir, bugreport_zip_path)

        # Extract bugreport zip and remove it
        os.makedirs(bugreport_dir, exist_ok=True)
        unzip_and_delete(bugreport_zip_path, bugreport_dir)

        # Find bugreport txt file
        bugreport_txt_path = next(
            iter(glob.glob(str(bugreport_dir / "bugreport*.txt"))), None
        )
        if not bugreport_txt_path:
            print("No bugreport*.txt file found")
            return
        else:
            bugreport_txt_path = Path(bugreport_txt_path)
            bugreport_dirs.bugreport_txt = bugreport_txt_path

        anr_files_dir = bugreport_dir / "FS" / "data" / "anr"
        if os.path.isdir(anr_files_dir):
            os.chdir(anr_files_dir)
            print(os.getcwd())

            # Unzip all zip files in this folder
            for file in os.listdir(anr_files_dir):
                print(file)
                bugreport_dirs.anr_files.append(anr_files_dir / file)
        else:
            print("No anr folder found")

        # Check if specific bugreport folder exists
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
                    bugreport_dirs.miuilog_scout_dirs.append(scout_app_dir / zip_file)
            if (scout_sys_dir := scout_mqs_dir / "sys") and os.path.isdir(
                scout_sys_dir
            ):
                for zip_file in os.listdir(scout_sys_dir):
                    print(zip_file)
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

        print(bugreport_dirs)
        return bugreport_dirs
