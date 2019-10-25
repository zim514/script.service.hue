# -*- coding: utf-8 -*-
import logging

from resources.lib import menu
from resources.lib import logger, ADDONVERSION, KODIVERSION

logger.info("*** Starting plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    menu.menu()  # Run menu
except Exception:
    logger.exception("Command exception")
logger.info("*** Shutting down plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
