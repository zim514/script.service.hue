# -*- coding: utf-8 -*-
import logging

from resources.lib import menu, commands
from resources.lib import logger, ADDONVERSION, KODIVERSION

logger.info("*** Starting script.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    commands.commands()  # Run menu
except Exception:
    logger.exception("Menu exception")
logger.info("*** Shutting down script.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
