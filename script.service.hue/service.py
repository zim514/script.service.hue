# -*- coding: utf-8 -*-
import logging

from resources.lib import globals
from resources.lib import kodilogging
from resources.lib import core

kodilogging.config()
logger = logging.getLogger(globals.ADDONID)

if globals.DEBUG:
    try:
        import sys;sys.path.append("e:\dev\pysrc")
        import pydevd
        pydevd.settrace('localhost', stdoutToServer=False, stderrToServer=False, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=False, overwrite_prev_trace=True, patch_multiprocessing=True)

    except ImportError:
        logger.critical("Kodi Hue Remote Debug Error: You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG")


logger.info("Starting service.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION))
core.service() #Run Hue service
logger.info("Shutting down service.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION ))


if globals.DEBUG is True:
    pydevd.stoptrace()