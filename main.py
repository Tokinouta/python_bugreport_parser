import typer
from python_bugreport_parser.cli import main as cli_main


if __name__ == "__main__":
    typer.run(cli_main)

# TODO: don't create output dir when the download link doesn't exist
