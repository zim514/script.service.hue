# -*- coding: utf-8 -*-


from resources.lib import menu, logger, ADDONVERSION, KODIVERSION,reporting


logger.info("*** Starting plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    menu.menu()  # Run menu
except Exception as exc:
    logger.exception("Command exception")
    reporting.process_exception(exc)
logger.info("*** Shutting down plugin.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
