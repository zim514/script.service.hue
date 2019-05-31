'''
Created on Apr. 22, 2019


'''
global settingsChanged
global connected 
global forceOnSunset
global daylightDisable
global separateLogFile
global logLevel


settingsChanged = False
connected = False
daylight = False
forceOnSunset = True
daylightDisable = True
separateLogFile = False
logLevel = 0


NUM_GROUPS = 1
STRDEBUG = False #Show string ID in UI 
DEBUG = False # Enable python remote debug
REMOTE_DBG_SUSPEND = False #Auto suspend thread when debugger attached






#ADDON = xbmcaddon.Addon()
#logger = logging.getLogger(ADDON.getAddonInfo('id'))
#kodilogging.config()