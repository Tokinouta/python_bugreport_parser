import python_bugreport_parser
from python_bugreport_parser.bugreport import Bugreport
from python_bugreport_parser.cli import parse_cli
from python_bugreport_parser.plugins import PluginRepo

cli_args = parse_cli()
print(cli_args)

bugreport_zip_path = cli_args.file_name
a = Bugreport.from_zip(bugreport_zip_path, "1234")
PluginRepo.analyze_all(a.bugreport_txt)
print(PluginRepo.report_all())