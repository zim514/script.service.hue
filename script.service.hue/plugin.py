# -*- coding: utf-8 -*-


from resources.lib import menu, logger, ADDONVERSION, KODIVERSION
import rollbar

logger.info("*** Starting plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    menu.menu()  # Run menu
except Exception as exc:
    logger.exception("Command exception")
    rollbar.kodi.report_error(access_token='b871c6292a454fb490344f77da186e10', version=ADDONVERSION, url="plugin.py")
logger.info("*** Shutting down plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
