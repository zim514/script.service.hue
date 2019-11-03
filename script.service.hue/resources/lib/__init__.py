import functools
import time
from logging import getLogger
from threading import Event

import xbmc
import xbmcaddon
import simplecache

from resources.lib import kodilogging
from resources.lib.kodisettings import settings_storage

NUM_GROUPS = 2  # group0= video, group1=audio
STRDEBUG = False  # Show string ID in UI
DEBUG = False  # Enable python remote debug
REMOTE_DBG_SUSPEND = False  # Auto suspend thread when debugger attached
QHUE_TIMEOUT = 0.5  # passed to requests, in seconds.
MINIMUM_COLOR_DISTANCE = 0.005
SETTINGS_CHANGED = Event()

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile'))  # .decode('utf-8'))
ADDONPATH = xbmc.translatePath(ADDON.getAddonInfo("path"))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')


logger = getLogger(ADDONID)
kodilogging.config()

cache = simplecache.SimpleCache()


def timer(func):
    """Logs the runtime of the decorated function"""
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        startTime = time.time()    # 1
        value = func(*args, **kwargs)
        endTime = time.time()      # 2
        runTime = endTime - startTime    # 3
        settings_storage['processTimes'].append(runTime)

        return value
    return wrapper_timer