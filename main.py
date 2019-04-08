# -*- coding: utf-8 -*-
import sys
import logging


import xbmcaddon

from resources.lib import kodilogging
from resources.lib import service


# Keep this file to a minimum, as Kodi
# doesn't keep a compiled copy of this
ADDON = xbmcaddon.Addon()
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
                        trace_only_current_thread=False,patch_multiprocessing=True)
        
    except ImportError:
        sys.stderr.write("Kodi Hue Remote Debug Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable REMOTE_DBG")
        sys.exit(1)


service.run()


