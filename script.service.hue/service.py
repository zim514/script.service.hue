# -*- coding: utf-8 -*-
import logging

from resources.lib import core
from resources.lib import globals
from resources.lib import kodilogging

kodilogging.config()
logger = logging.getLogger(globals.ADDONID)

logger.info("Starting service.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION))
try:
    core.service() #Run Hue service
except Exception:
    logger.exception("Core service exception")
logger.info("Shutting down service.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION ))
