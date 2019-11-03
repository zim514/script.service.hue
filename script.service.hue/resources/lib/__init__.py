import functools
import time
from logging import getLogger

import xbmc, xbmcaddon, simplecache

from resources.lib.globals import processTimes, performanceLogging

NUM_GROUPS = 2  # group0= video, group1=audio
STRDEBUG = False  # Show string ID in UI
DEBUG = False  # Enable python remote debug
REMOTE_DBG_SUSPEND = False  # Auto suspend thread when debugger attached
QHUE_TIMEOUT = 0.5  # passed to requests, in seconds.
MINIMUM_COLOR_DISTANCE = 0.005

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile'))  # .decode('utf-8'))
ADDONPATH = xbmc.translatePath(ADDON.getAddonInfo("path"))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')

from resources.lib import kodilogging
logger = getLogger(ADDONID)
kodilogging.config()

cache = simplecache.SimpleCache()
settings = cache.get("script.service.hue.settings")


def timer(func):
    """Logs the runtime of the decorated function"""
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        startTime = time.time()    # 1
        value = func(*args, **kwargs)
        endTime = time.time()      # 2
        runTime = endTime - startTime    # 3
        processTimes.append(runTime)
        if performanceLogging:
            logger.debug("[{}] Completed in {:02.0f}ms".format(func.__name__,runTime*1000))
        return value
    return wrapper_timer