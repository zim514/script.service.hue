

from logging import getLogger
from xbmcaddon import Addon
#getInfoLabel, translatePath 

from kodi_six import xbmcaddon, xbmc

NUM_GROUPS = 1
STRDEBUG = False #Show string ID in UI
DEBUG = False # Enable python remote debug
REMOTE_DBG_SUSPEND = False #Auto suspend thread when debugger attached

ADDON = Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile')) #.decode('utf-8'))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')
logger = getLogger(ADDONID)

settingsChanged = False
connected = False
daylight = False
forceOnSunset = True
daylightDisable = True
separateLogFile = False


