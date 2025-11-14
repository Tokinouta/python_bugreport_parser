import typer
from python_bugreport_parser.cli import main as cli_main
# from python_bugreport_parser.repl import start_repl


if __name__ == "__main__":
    typer.run(cli_main)
    # start_repl()

# TODO: don't create output dir when the download link doesn't exist
