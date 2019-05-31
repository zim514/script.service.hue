# -*- coding: utf-8 -*-
import logging

import xbmcaddon
from xbmc import getInfoLabel

from resources.lib import globals
from resources.lib import kodilogging
from resources.lib import core

kodilogging.config()
logger = logging.getLogger(__name__)
logger.debug("Loading {} service.py, version {}, Kodi: {}".format(globals.ADDONID, globals.ADDONVERSION, globals.KODIVERSION ) )

if globals.DEBUG:
    try:
        import threading
        import pydevd

        threading.Thread.name = 'script.service.hue.service'
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        logger.debug("Kodi Hue Remote Debug Error: " + 
                         "You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable REMOTE_DBG")
        exit(1)


core.service() #Run Hue service
logger.debug("'%s' shutting down service" % globals.ADDONID)

if globals.DEBUG is True:
    pydevd.stoptrace()