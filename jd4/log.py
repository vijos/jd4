import coloredlogs
import os
from coloredlogs import syslog
from logging import getLogger, DEBUG

if 'JD4_USE_SYSLOG' not in os.environ:
    coloredlogs.install(
        level=DEBUG,
        fmt='[%(levelname).1s %(asctime)s %(module)s:%(lineno)d] %(message)s',
        datefmt='%y%m%d %H:%M:%S')
else:
    syslog.enable_system_logging(
        level=DEBUG,
        fmt='jd4[%(process)d] %(programname)s %(levelname).1s %(message)s')

logger = getLogger(__name__)
