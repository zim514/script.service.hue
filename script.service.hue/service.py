# -*- coding: utf-8 -*-


from resources.lib import core, logger, ADDONVERSION, KODIVERSION
import rollbar.kodi

logger.info("Starting service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    core.core() #Run Hue service
except Exception as exc:
    logger.exception("Core service exception")
    rollbar.kodi.report_error(access_token='b871c6292a454fb490344f77da186e10', version=ADDONVERSION)

logger.info("Shutting down service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
