# -*- coding: utf-8 -*-
import logging
import xbmc

from resources.lib import globals
from resources.lib import kodilogging
from resources.lib import core

#kodilogging.config()
#logger = logging.getLogger(__name__)

xbmc.log("Loading {} default.py, version {}, Kodi: {}".format(globals.ADDONID, globals.ADDONVERSION, globals.KODIVERSION ),xbmc.LOGNOTICE)

if globals.DEBUG:
    try:
        import threading
        import pydevd

        threading.Thread.name = 'script.service.hue.menu'
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        xbmc.log("Kodi Hue Remote Debug Error: You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG")
        


core.menu() #Run menu
xbmc.log("Shutting down.",xbmc.LOGNOTICE)

if globals.DEBUG is True:
    pydevd.stoptrace()