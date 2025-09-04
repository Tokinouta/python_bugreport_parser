from datetime import datetime
from pathlib import Path
import tomllib
import os

from python_bugreport_parser.plugins import BugreportAnalysisContext, PluginRepo
from python_bugreport_parser.download import download_one_file


# CONFIG_PATH = Path(__file__).parent / "config/config.toml"
# with open(CONFIG_PATH, "rb") as f:
#     config = tomllib.load(f)
# extract_path = Path(config["extract_path"])

def main():
    feedback_ids = ["115450951"]

    home_dir = os.getenv("HOME")
    if not home_dir:
        home_dir = "."

    for id in feedback_ids:
        user_feedback_path = Path(os.path.join(home_dir, "jira", "FEEDBACK-77143"))
        context = BugreportAnalysisContext()
        bugreport = download_one_file(id, user_feedback_path)
        if bugreport is None:
            print(f"download bugreport {id} failed")
            continue
        else:
            context.bugreport = bugreport
        PluginRepo.run_all(context)
        with open(f"output-{id}.txt", "w", encoding="utf-8") as file:
            file.write(PluginRepo.report_all())

if __name__ == "__main__":
    main()