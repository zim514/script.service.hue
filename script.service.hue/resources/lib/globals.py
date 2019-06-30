

from logging import getLogger
from xbmcaddon import Addon


from kodi_six import xbmcaddon, xbmc

NUM_GROUPS = 2  #group0= video, group1=audio
STRDEBUG = False #Show string ID in UI
DEBUG = False # Enable python remote debug
REMOTE_DBG_SUSPEND = False #Auto suspend thread when debugger attached

ADDON = Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONDIR = xbmc.translatePath(ADDON.getAddonInfo('profile')) #.decode('utf-8'))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')
logger = getLogger(ADDONID)


#Init values for code completion, all get overwritten by kodiHue.loadSettings()
settingsChanged = False
connected = False
daylight = False
forceOnSunset = False
daylightDisable = False
separateLogFile = False
initialFlash = False
reloadFlash = False
enableSchedule = False


startTime = ""
endTime = ""

lastMediaType=0


