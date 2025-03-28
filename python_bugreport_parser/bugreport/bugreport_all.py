from pathlib import Path
from typing import List

from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt


class BugreportDirs:
    def __init__(self):
        self.bugreport_txt = Path()
        self.anr_files_dir = Path()
        self.miuilog_reboot_dir = Path()
        self.miuilog_scout_dir = Path()


class Bugreport:
    def __init__(self):
        self.bugreport_txt: BugreportTxt = None
        self.anr_files: List[str] = []
        self.miuilog_reboots: List[str] = []
        self.miuilog_scouts: List[str] = []
