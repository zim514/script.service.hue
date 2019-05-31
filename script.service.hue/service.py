# -*- coding: utf-8 -*-
import logging

import xbmcaddon
from xbmc import getInfoLabel

from resources.lib import kodilogging
from resources.lib import core
from resources.lib import globals

# Keep this file to a minimum, as Kodi
# doesn't keep a compiled copy of this
ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')

kodilogging.config()
logger = logging.getLogger(__name__)

logger.debug("Loading {} version {}, Kodi: {}".format(ADDONID, ADDONVERSION, getInfoLabel('System.BuildVersion') ) )


if globals.DEBUG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    
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


core.service()

logger.debug("'%s' shutting down service" % ADDONID)
if globals.DEBUG is True:
    pydevd.stoptrace()