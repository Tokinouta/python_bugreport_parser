import os
import zipfile
from pathlib import Path


def unzip_and_delete(zip_file: Path, unzip_dir: Path) -> None:
    """
    Unzip the specified zip file into the given directory and then delete the zip file.

    Args:
        zip_file (Path): Path object pointing to the zip file to be extracted.
        unzip_dir (Path): Path object pointing to the directory where the contents will be extracted.

    Raises:
        zipfile.BadZipFile: If the provided file is not a valid zip file.
        PermissionError: If there is a permission issue while reading the zip file or deleting files.
        FileNotFoundError: If the provided zip file does not exist.
    """
    os.makedirs(unzip_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(unzip_dir)
        os.remove(zip_file)
    except (zipfile.BadZipFile, PermissionError, FileNotFoundError) as e:
        print(f"Error processing {zip_file}: {e}")
        # Optionally, delete the partially extracted directory
        if unzip_dir.exists():
            os.remove(unzip_dir)
        raise e
