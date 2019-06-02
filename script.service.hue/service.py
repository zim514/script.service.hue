# -*- coding: utf-8 -*-
import logging

from resources.lib import globals
from resources.lib import kodilogging
from resources.lib import core

logger = kodilogging.config()
#logger = logging.getLogger(__name__)
logger.info("XXXXXXXXXXXXXXXXLoading {} service.py, version {}, Kodi: {}".format(globals.ADDONID, globals.ADDONVERSION, globals.KODIVERSION ) )

if globals.DEBUG:
    try:
        import threading
        import pydevd

        threading.Thread.name = 'script.service.hue.service'
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        logger.debug("Kodi Hue Remote Debug Error: " + 
                         "You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG")
        exit(1)


core.service() #Run Hue service
logger.debug("Shutting down service")

if globals.DEBUG is True:
    pydevd.stoptrace()