from datetime import datetime
from pathlib import Path
import tomllib
import os

from python_bugreport_parser.plugins import BugreportAnalysisContext, PluginRepo
from python_bugreport_parser.download import download_one_file


CONFIG_PATH = Path(__file__).parent / "config/config.toml"
with open(CONFIG_PATH, "rb") as f:
    config = tomllib.load(f)
extract_path = Path(config["extract_path"])

feedback_ids = [
    "115486261"
]

home_dir = os.getenv("HOME")
if not home_dir:
    home_dir = "."

for id in feedback_ids:
    user_feedback_path = os.path.join(home_dir, "jira", "OS3-feedback", id)
    context = BugreportAnalysisContext()
    context.bugreport = download_one_file(id, user_feedback_path)
    PluginRepo.run_all(context)
    with open(
        "/home/dayong/workspace/others/code/python_bugreport_parser/output.txt",
        "w",
        encoding="utf-8",
    ) as file:
        file.write(PluginRepo.report_all())
