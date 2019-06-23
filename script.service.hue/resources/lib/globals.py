

from logging import getLogger
from xbmcaddon import Addon
from xbmc import getInfoLabel, translatePath

NUM_GROUPS = 1
STRDEBUG = False #Show string ID in UI
DEBUG = False # Enable python remote debug
REMOTE_DBG_SUSPEND = False #Auto suspend thread when debugger attached

ADDON = Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = translatePath(ADDON.getAddonInfo('profile').decode('utf-8'))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = getInfoLabel('System.BuildVersion')
logger = getLogger(ADDONID)

settingsChanged = False
connected = False
daylight = False
forceOnSunset = True
daylightDisable = True
separateLogFile = False


