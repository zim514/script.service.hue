# -*- coding: utf-8 -*-


from resources.lib import core, logger, ADDONVERSION, KODIVERSION
from resources.lib import reporting

logger.info("Starting service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    core.core() #Run Hue service
except Exception as exc:
    logger.exception("Core service exception")
    reporting.process_exception(exc)

logger.info("Shutting down service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
