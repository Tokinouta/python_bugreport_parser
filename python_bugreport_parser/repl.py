import cmd
import shlex
from pathlib import Path
from typing import List, Optional

from typer import Typer

from python_bugreport_parser.bugreport.bugreport_all import Log284
from python_bugreport_parser.plugins import BugreportAnalysisContext, PluginRepo
from python_bugreport_parser.cli import main as cli_main


class BugReportREPL(cmd.Cmd):
    intro = 'Welcome to the Bug Report Parser REPL. Type help or ? to list commands.\n'
    prompt = '(bugreport) '
    
    def __init__(self):
        super().__init__()
        self.bugreport: Optional[Log284] = None
        self.context: Optional[BugreportAnalysisContext] = None
        self.app = Typer(add_completion=False)
        self.app.command()(cli_main)


    def do_load(self, args: str) -> None:
        """
        Load a bugreport from a zip file or directory.
        Usage: 
          load <path_to_zip_or_directory>
          load inspect <section_name>
        """
        # Parse arguments
        arg_parts = shlex.split(args.strip())
        
        # Handle subcommands
        if len(arg_parts) >= 2 and arg_parts[0] == "inspect":
            # Handle load inspect <section_name>
            self._load_inspect(arg_parts[1])
            return
        elif len(arg_parts) >= 1 and arg_parts[0] == "inspect":
            print("Please provide a section name to inspect.")
            print("Usage: load inspect <section_name>")
            return
            
        # Original load functionality
        if not args:
            print("Please provide a path to the bugreport zip file or directory")
            return
            
        path = Path(args.strip())
        if not path.exists():
            print(f"Path {path} does not exist")
            return
            
        if path.is_file() and path.suffix == '.zip':
            # Load from zip file
            feedback_dir = path.parent / "feedback_temp"
            self.bugreport = Log284.from_zip(path, feedback_dir)
        elif path.is_dir():
            # Load from directory
            self.bugreport = Log284.from_dir(path)
        else:
            print("Please provide a valid zip file or directory path")
            return
            
        if self.bugreport:
            print("Bugreport loaded successfully")
            self.context = BugreportAnalysisContext()
            self.context.bugreport = self.bugreport
        else:
            print("Failed to load bugreport")

    def _load_inspect(self, section_name: str) -> None:
        """
        Inspect a specific section of the loaded bugreport.
        This is a helper method for the 'load inspect' subcommand.
        """
        if not self.bugreport or not self.bugreport.bugreport:
            print("No bugreport loaded. Use 'load <path>' command first.")
            return
            
        if not section_name:
            print("Please provide a section name to inspect.")
            print("Use 'load list_sections' to see available sections.")
            return
        
        try:
            sections = self.bugreport.bugreport.bugreport_txt.sections
            target_section = None
            for section in sections:
                if section.name == section_name:
                    target_section = section
                    break
                    
            if not target_section:
                print(f"Section '{section_name}' not found.")
                print("Use 'list_sections' to see available sections.")
                return
                
            # Display section information
            print(f"Section: {target_section.name}")
            print(f"Lines: {target_section.start_line}-{target_section.end_line}")
            print(f"Content preview:")
            
            # Show the content of the section
            lines = self.bugreport.bugreport.bugreport_txt.lines
            start_idx = target_section.start_line - 1  # Convert to 0-based indexing
            end_idx = target_section.end_line  # End line is exclusive
            
            for i in range(start_idx, min(end_idx, len(lines))):
                print(f"{i+1:4d}: {lines[i]}")
                
        except Exception as e:
            print(f"Error inspecting section: {e}")

    def do_analyze(self, args: str) -> None:
        """
        Analyze the loaded bugreport using all plugins.
        Usage: analyze
        """
        if not self.bugreport or not self.context:
            print("No bugreport loaded. Use 'load' command first.")
            return
            
        try:
            PluginRepo.run_all(self.context)
            print("Analysis completed")
        except Exception as e:
            print(f"Error during analysis: {e}")

    def do_report(self, args: str) -> None:
        """
        Generate and display reports from all plugins.
        Usage: report
        """
        if not self.context:
            print("No analysis context. Use 'load' and 'analyze' commands first.")
            return
            
        try:
            report = PluginRepo.report_all()
            print(report)
        except Exception as e:
            print(f"Error generating report: {e}")

    def do_list_sections(self, args: str) -> None:
        """
        List all sections in the loaded bugreport.
        Usage: list_sections
        """
        if not self.bugreport or not self.bugreport.bugreport:
            print("No bugreport loaded. Use 'load' command first.")
            return
            
        try:
            sections = self.bugreport.bugreport.bugreport_txt.sections
            print(f"Found {len(sections)} sections:")
            for section in sections:
                print(f"  - {section.name} (lines {section.start_line}-{section.end_line})")
        except Exception as e:
            print(f"Error listing sections: {e}")

    def do_quit(self, args: str) -> bool:
        """
        Quit the REPL.
        Usage: quit
        """
        print("Goodbye!")
        return True

    def do_exit(self, args: str) -> bool:
        """
        Exit the REPL.
        Usage: exit
        """
        return self.do_quit(args)

    def emptyline(self) -> bool:
        """
        Do nothing on empty line.
        """
        return False
    
    def default(self, line: str) -> None:
        parts = shlex.split(line)
        try:
            # The first argument in list is program name placeholder
            self.app([ "", *parts ])
        except SystemExit as e:
            # On typos or help requests, Click/Typer may call exit(0/1)
            # We catch so REPL remains
            # Optionally inspect e.code
            pass
        except Exception as exc:
            print(f"Error: {exc}")

    def do_help(self, args: str) -> None:
        """
        Show help for a specific command.
        Usage: help <command>
        """
        if not args:
            print("Please provide a command to get help for.")
            return
            
        try:
            command = self.app.get_command(args)
            if command:
                print(command.get_help())
            else:
                print(f"Command '{args}' not found.")
        except Exception as e:
            pass

def start_repl() -> None:
    # """Start the Bug Report Parser REPL."""
    repl = BugReportREPL()
    repl.cmdloop()
    # print("Welcome to MyREPL. Type ‘help’ or empty to list commands.")
    # app = Typer(add_completion=False)
    # app.command()(cli_main)
    # while True:
    #     try:
    #         raw = input("myapp> ")
    #     except (EOFError, KeyboardInterrupt):
    #         print("\nBye!")
    #         break
    #     line = raw.strip()
    #     if not line:
    #         continue
    #     if line in ("exit", "quit"):
    #         print("Bye!")
    #         break
    #     parts = shlex.split(line)
    #     try:
    #         # The first argument in list is program name placeholder
    #         app([ "", *parts ])
    #     except SystemExit as e:
    #         # On typos or help requests, Click/Typer may call exit(0/1)
    #         # We catch so REPL remains
    #         # Optionally inspect e.code
    #         pass
    #     except Exception as exc:
    #         print(f"Error: {exc}")