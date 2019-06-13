# -*- coding: utf-8 -*-
import logging
import xbmc

from resources.lib import globals
from resources.lib import kodilogging
from resources.lib import core

kodilogging.config()
logger = logging.getLogger(globals.ADDONID)



logger.info("Starting default.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION ))

if globals.DEBUG:
    try:
        import sys;sys.path.append("e:\dev\pysrc")
        import pydevd
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        logger.debug("Kodi Hue Remote Debug Error: You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG")
        


core.menu() #Run menu
logger.info("Shutting down default.py, version {}, Kodi: {}".format(globals.ADDONVERSION, globals.KODIVERSION ))

if globals.DEBUG:
    pydevd.stoptrace()