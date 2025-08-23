import os
import zipfile
from pathlib import Path


def unzip_and_delete(zip_file: Path, unzip_dir: Path):
    os.makedirs(unzip_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(unzip_dir)
        os.remove(zip_file)
    except (zipfile.BadZipFile, PermissionError, FileNotFoundError) as e:
        print(f"Error processing {zip_file}: {e}")
