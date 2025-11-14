# Bugreport Parser

This is an attempt to automize the analysis of Android bugreports. There are too many vanilla cases that contain no effective information of the reported issue. Such a script will spare me more time on such dull stuffs.

## Project architecture

Currently, there are two main components. 

- bugreport: This models the bugreport zip and its contents inside, accompanied by some basic loading, parsing and searching functionality
- plugin: This extends the ability of checking specific causes of issues

Under construction. Use with causion.

## Interactive Mode (REPL)

The project includes an interactive REPL (Read-Eval-Print Loop) for exploring bug reports:

```bash
python -m python_bugreport_parser.cli /path/to/output --id /path/to/bugreport.zip --repl
```

In the REPL, you can use the following commands:
- `load <path>` - Load a bugreport from a zip file or directory
- `analyze` - Analyze the loaded bugreport using all plugins
- `report` - Generate and display reports from all plugins
- `list_sections` - List all sections in the loaded bugreport
- `quit` or `exit` - Exit the REPL

PAY ATTENTION: The REPL is still under construction. And further development is suspended.

## Test cases

- MUT-367665