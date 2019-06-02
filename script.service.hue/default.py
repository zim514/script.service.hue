# -*- coding: utf-8 -*-
import logging

from resources.lib import globals
from resources.lib import kodilogging
from resources.lib import core

kodilogging.config()
logger = logging.getLogger(__name__)
logger.debug("Loading {} default.py, version {}, Kodi: {}".format(globals.ADDONID, globals.ADDONVERSION, globals.KODIVERSION ) )

if globals.DEBUG:
    try:
        import threading
        import pydevd

        threading.Thread.name = 'script.service.hue.menu'
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        logger.debug("Kodi Hue Remote Debug Error: " + 
                         "You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG")
        exit(1)


core.menu() #Run menu
logger.debug("Shutting down menu")

if globals.DEBUG is True:
    pydevd.stoptrace()