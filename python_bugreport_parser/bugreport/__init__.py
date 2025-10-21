import logging

# Configure logging for the bugreport package
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Default level, can be overridden by the application

# Create handler if not already configured
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)

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