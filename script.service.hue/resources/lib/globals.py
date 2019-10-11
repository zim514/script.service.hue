# -*- coding: utf-8 -*-
import functools
import time

from logging import getLogger
from collections import deque

import xbmc,xbmcaddon

NUM_GROUPS = 2  #group0= video, group1=audio
STRDEBUG = False #Show string ID in UI
DEBUG = False # Enable python remote debug
REMOTE_DBG_SUSPEND = False #Auto suspend thread when debugger attached
QHUE_TIMEOUT = 0.5 #passed to requests, in seconds.


ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile')) #.decode('utf-8'))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')
logger = getLogger(ADDONID)


settingsChanged = False
connected = False
daylight = False
forceOnSunset = False
daylightDisable = False
separateLogFile = False
initialFlash = False
reloadFlash = False
enableSchedule = False
performanceLogging = False
ambiEnabled = False
connectionMessage = False

videoMinimumDuration = 0
video_enableMovie  = True
video_enableEpisode = True
video_enableMusicVideo = True
video_enableOther = True

lastMediaType=0

startTime = ""
endTime = ""
processTimes = deque(maxlen=100)
averageProcessTime = 0


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
