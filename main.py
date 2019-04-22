# -*- coding: utf-8 -*-
import logging
import sys

import xbmcaddon

from resources.lib import kodilogging
from resources.lib import service

global settingsChanged
global connected

# Keep this file to a minimum, as Kodi
# doesn't keep a compiled copy of this
ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))
kodilogging.config()

REMOTE_DBG = True
REMOTE_DBG_SUSPEND = False

if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:

        sys.path.append('e:\dev\pysrc')
        import pydevd

        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        sys.stderr.write("Kodi Hue Remote Debug Error: " + 
                         "You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable REMOTE_DBG")
        sys.exit(1)

service.run()
