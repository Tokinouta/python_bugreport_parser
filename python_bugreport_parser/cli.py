import typer
from dataclasses import dataclass
from pathlib import Path
from typing_extensions import Annotated

from python_bugreport_parser.bugreport.bugreport_all import Bugreport, Log284
from python_bugreport_parser.plugins import BugreportAnalysisContext, PluginRepo
from python_bugreport_parser.download import download_one_file


@dataclass
class CliArgs:
    """Data class for storing CLI arguments"""

    path: Path
    feedback_id: str
    download: bool
    analyse: bool
    idsubdir: bool


def main(
    path: Annotated[Path, typer.Argument(help="Path for processing")],
    feedback_id: Annotated[str, typer.Option("--id", help="Feedback ID, a feedback ID number or a path to zipped 284 log", show_default=False)],
    download: Annotated[
        bool, typer.Option("--download", help="Download the bugreport", show_default=True)
    ] = False,
    analyse: Annotated[
        bool, typer.Option("--analyse", help="Analyse the bugreport", show_default=True)
    ] = False,
    idsubdir: Annotated[
        bool,
        typer.Option(
            "--idsubdir",
            help="Append the ID to the end of the path as a new subdirectory",
            show_default=True,
        ),
    ] = False,
) -> None:
    """Bugreport processing CLI tool"""
    # If neither download nor analyse is specified, do both
    # if not download and not analyse:
    #     download = True
    #     analyse = True

    args = CliArgs(
        path=path, feedback_id=feedback_id, download=download, analyse=analyse, idsubdir=idsubdir
    )
    process_bugreport(args)

def process_bugreport(cli_args: CliArgs) -> None:
    """Process bugreport according to CLI arguments"""
    print(cli_args)
    feedback_id: str = cli_args.feedback_id
    base_path: Path = cli_args.path

    # If --idsubdir option is specified, append the ID to the path
    if cli_args.idsubdir:
        user_feedback_path: Path = base_path / feedback_id
    else:
        user_feedback_path: Path = base_path

    # Create the directory if it doesn't exist
    user_feedback_path.mkdir(parents=True, exist_ok=True)

    # Download if requested
    bugreport = None
    if cli_args.download:
        bugreport = download_one_file(feedback_id, user_feedback_path)
        if bugreport is None:
            print(f"Download bugreport {feedback_id} failed")
            return
    else:
        zip_file = Path(feedback_id)
        bugreport = Log284.from_zip(zip_file, user_feedback_path)

    # Analyse if requested
    if cli_args.analyse:
        context = BugreportAnalysisContext()
        if bugreport is None:
            # Try to load existing bugreport if we didn't download one
            # You might need to implement loading logic here
            print("Analysis requested but no bugreport available")
            return

        context.bugreport = bugreport
        PluginRepo.run_all(context)

        # Save analysis output
        output_file: Path = user_feedback_path / f"output.txt"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(PluginRepo.report_all())
