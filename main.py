from datetime import datetime
from pathlib import Path
import tomllib
import os

from python_bugreport_parser.bugreport.bugreport_all import Log284
from python_bugreport_parser.plugins import BugreportAnalysisContext, PluginRepo
from python_bugreport_parser.download import download_one_file


CONFIG_PATH = Path(__file__).parent / "config/config.toml"
with open(CONFIG_PATH, "rb") as f:
    config = tomllib.load(f)
extract_path = Path(config["extract_path"])

# feedback_id = "113280755"
# feedback_dir = extract_path / str(feedback_id)
# a = Log284.from_dir(feedback_dir)
# a.bugreport.bugreport_txt.error_timestamp = datetime(2025, 4, 6, 15, 40, 0)
home_dir = os.getenv("HOME")
if not home_dir:
    home_dir = "."
user_feedback_path = os.path.join(home_dir, "jira", "UTUG-60303")

context = BugreportAnalysisContext()
context.bugreport = download_one_file("114302618", user_feedback_path)
context.bugreport = Log284.from_dir(user_feedback_path)
PluginRepo.run_all(context)
with open(
    "/home/dayong/workspace/others/code/python_bugreport_parser/output.txt",
    "w",
    encoding="utf-8",
) as file:
    file.write(PluginRepo.report_all())
