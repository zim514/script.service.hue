from logging import getLogger

import xbmc, xbmcaddon

NUM_GROUPS = 2  # group0= video, group1=audio
STRDEBUG = False  # Show string ID in UI
DEBUG = False  # Enable python remote debug
REMOTE_DBG_SUSPEND = False  # Auto suspend thread when debugger attached
QHUE_TIMEOUT = 0.5  # passed to requests, in seconds.

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile'))  # .decode('utf-8'))
ADDONPATH = xbmc.translatePath(ADDON.getAddonInfo("path"))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')

from resources.lib import kodilogging
logger = getLogger(ADDONID)
kodilogging.config()