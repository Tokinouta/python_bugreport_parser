from python_bugreport_parser.bugreport.bugreport_all import Bugreport
from python_bugreport_parser.bugreport.bugreport_txt import BugreportTxt, Metadata
from python_bugreport_parser.bugreport.section import (
    Section,
    DumpsysSection,
    LogcatSection,
    SystemPropertySection,
    AnrRecordSection,
    OtherSection,
    LogcatLine,
    DumpsysEntry
)
from python_bugreport_parser.bugreport.metadata import Metadata
from python_bugreport_parser.bugreport.dumpsys_entry import MqsServiceDumpsysEntry

# TODO: There is actually one more layer of abstraction, which I call 284 log here. 
# 284 log -> Bugreport -> BugreportTxt
# Now we have the latter two, but the first is still missing.