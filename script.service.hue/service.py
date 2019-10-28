# -*- coding: utf-8 -*-
import logging

from resources.lib import core, logger, ADDONVERSION, KODIVERSION
from resources.lib import globals
from resources.lib import kodilogging


logger.info("Starting service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    core.core() #Run Hue service
except Exception:
    logger.exception("Core service exception")
logger.info("Shutting down service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
