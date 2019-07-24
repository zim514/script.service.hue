# -*- coding: utf-8 -*-
import logging

from resources.lib import core
from resources.lib import globals
from resources.lib import kodilogging

kodilogging.config()
logger = logging.getLogger(globals.ADDONID)

if globals.DEBUG:
    try:
        import pydevd
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=False,
                        trace_only_current_thread=False, overwrite_prev_trace=False, patch_multiprocessing=False)
    except ImportError:
        logger.exception("Kodi Hue Remote Debug Error: You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG")

logger.info("Starting service.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION))
try:
    core.service() #Run Hue service
except Exception:
    logger.exception("Core service exception")
logger.info("Shutting down service.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION ))
