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
        self.anr_files_dir = Path()
        self.miuilog_reboot_dir: List[Path] = []
        self.miuilog_scout_dir: List[Path] = []


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

        # Check if specific bugreport folder exists
        reboot_mqs_dir = (
            bugreport_dir / "FS" / "data" / "miuilog" / "stability" / "reboot"
        )

        if os.path.isdir(reboot_mqs_dir):
            os.chdir(reboot_mqs_dir)
            print(os.getcwd())

            # Unzip all zip files in this folder
            for zip_file in glob.glob("*.zip"):
                print(zip_file)
                extract_dir = os.path.splitext(zip_file)[0]
                os.makedirs(extract_dir, exist_ok=True)
                unzip_and_delete(zip_file, extract_dir)
                print(f"Unzipped {zip_file} to {extract_dir}")
                bugreport_dirs.miuilog_reboot_dir.append(Path(extract_dir))
        else:
            print("No reboot mqs folder found")

        return bugreport_dirs
