# -*- coding: utf-8 -*-
import logging
import xbmc

from resources.lib import globals
#from resources.lib import kodilogging
from resources.lib import core
from resources.lib import kodiutils

#logger = kodilogging.config()


#loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]

if globals.DEBUG:
    try:
        import threading
        import sys;sys.path.append("e:\dev\pysrc")
        import pydevd

        threading.Thread.name = 'script.service.hue.service'
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True, suspend=globals.REMOTE_DBG_SUSPEND,
                        trace_only_current_thread=True, overwrite_prev_trace=True, patch_multiprocessing=False)

    except ImportError:
        xbmc.log("Kodi Hue Remote Debug Error: You must add org.python.pydev.debug.pysrc to your PYTHONPATH, or disable DEBUG",xbmc.LOGERROR)



kodiutils.configLog()
#logger = logging.getLogger()
xbmc.log("[{}]: Starting service.py, version {}, Kodi: {}".format(globals.ADDONID, globals.ADDONVERSION, globals.KODIVERSION ),xbmc.LOGNOTICE )




core.service() #Run Hue service
xbmc.log("Shutting down service",xbmc.LOGNOTICE)

if globals.DEBUG is True:
    pydevd.stoptrace()