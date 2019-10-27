from logging import getLogger
from socket import getfqdn
from collections import deque
import datetime

import xbmc
import xbmcgui

import requests
from .kodisettings import settings
from . import qhue
from resources.lib.qhue.qhue import QhueException

from . import KodiGroup
from . import globals
from .language import get_string as _

logger = getLogger(globals.ADDONID)


def loadSettings():
    logger.debug("Loading settings")
    globals.reloadFlash = globals.ADDON.getSettingBool("reloadFlash")
    globals.initialFlash = globals.ADDON.getSettingBool("initialFlash")
    globals.forceOnSunset = globals.ADDON.getSettingBool("forceOnSunset")
    globals.daylightDisable = globals.ADDON.getSettingBool("daylightDisable")
    
    globals.enableSchedule = globals.ADDON.getSettingBool("enableSchedule")
    globals.startTime = globals.ADDON.getSetting("startTime") #string HH:MM
    globals.endTime = globals.ADDON.getSetting("endTime") #string HH:MM
    globals.performanceLogging = globals.ADDON.getSettingBool("performanceLogging")
    globals.disableConnectionMessage = globals.ADDON.getSettingBool("disableConnectionMessage")

    globals.videoMinimumDuration = globals.ADDON.getSettingInt("video_MinimumDuration") #Setting in Minutes. Kodi library uses seconds, needs to be converted.
    globals.video_enableMovie = globals.ADDON.getSettingBool("video_Movie")
    globals.video_enableMusicVideo  = globals.ADDON.getSettingBool("video_MusicVideo")
    globals.video_enableEpisode = globals.ADDON.getSettingBool("video_Episode")
    globals.video_enableOther = globals.ADDON.getSettingBool("video_Other")
    
    globals.ambiEnabled = globals.ADDON.getSettingBool("group3_enabled") 
    validateSchedule()


def setupGroups(bridge, flash=False):
    logger.debug("in setupGroups()")
    kgroups= []
    
    if globals.ADDON.getSettingBool("group0_enabled"): #VIDEO Group
        kgroups.append(KodiGroup.KodiGroup())
        kgroups[0].setup(bridge, 0, flash,KodiGroup.VIDEO)

    if globals.ADDON.getSettingBool("group1_enabled"): #Audio Group
        kgroups.append(KodiGroup.KodiGroup())
        kgroups[1].setup(bridge, 1, flash,KodiGroup.AUDIO)

    return kgroups
    

def createHueScene(bridge):
    logger.debug("In kodiHue createHueScene")
    scenes=bridge.scenes
    
    xbmcgui.Dialog().ok(_("Create New Scene"),_("Adjust lights to desired state in the Hue App to save as new scene."),
                        _("Set a fade time in seconds, or set to 0 seconds for an instant transition."))
    
    sceneName = xbmcgui.Dialog().input(_("Scene Name"))
    
    if sceneName:
        transitionTime= xbmcgui.Dialog().numeric(0,_("Fade Time (Seconds)"),defaultt="10")
        selected = selectHueLights(bridge)
        
        if selected:
            res=scenes(lights=selected,name=sceneName,recycle=False,type='LightScene',http_method='post',transitiontime=int(transitionTime)*10) #Hue API transition time is in 100msec. *10 to convert to seconds.
            logger.debug("In kodiHue createHueScene. Res: {}".format(res))
            if res[0]["success"]:
                xbmcgui.Dialog().ok(_("Create New Scene"),_("Scene successfully created!"),_("You may now assign your Scene to player actions."))
            #   xbmcgui.Dialog().notification(_("Hue Service"), _("Scene Created"))
            else:
                xbmcgui.Dialog().ok(_("Error"),_("Error: Scene not created."))
    

def deleteHueScene(bridge):
    logger.debug("In kodiHue deleteHueScene")
    scene = selectHueScene(bridge)
    if scene is not None:
        confirm = xbmcgui.Dialog().yesno(_("Delete Hue Scene"), _("Are you sure you want to delete this scene: "), str(scene[1]))
    if scene and confirm:              
        scenes=bridge.scenes
        res=scenes[scene[0]](http_method='delete')
        logger.debug("In kodiHue createHueGroup. Res: {}".format(res))
        if res[0]["success"]:
            xbmcgui.Dialog().notification(_("Hue Service"), _("Scene deleted"))
        else:
            xbmcgui.Dialog().notification(_("Hue Service"), _("ERROR: Scene not created"))


def _discoverNupnp():
    logger.debug("In kodiHue discover_nupnp()")
    try:
        #ssl chain on new URL seems to be fixed
        #req = requests.get('https://www.meethue.com/api/nupnp')
        req = requests.get('https://discovery.meethue.com/')
    except requests.exceptions.ConnectionError as e:
        logger.info("Nupnp failed: {}".format(e))
        return None
    
    res = req.json()
    bridge_ip = None
    if res:
        bridge_ip = res[0]["internalipaddress"]
    return bridge_ip
        

def _discoverSsdp():
    from . import ssdp
    from urlparse import urlsplit

    ssdp_list = ssdp.discover("ssdp:all",timeout=5,mx=3)
    logger.debug("ssdp_list: {}".format(ssdp_list))
    
    bridges = [u for u in ssdp_list if 'IpBridge' in u.server]
    if bridges:
        ip = urlsplit(bridges[0].location).hostname
        logger.debug("ip: {}".format(ip))
        return ip
    return None


def bridgeDiscover(monitor):
    logger.debug("Start bridgeDiscover")
    #Create new config if none exists. Returns success or fail as bool
    globals.ADDON.setSettingString("bridgeIP","")   
    globals.ADDON.setSettingString("bridgeUser","")
    globals.connected = False

    progressBar = xbmcgui.DialogProgress()
    progressBar.create(_('Searching for bridge...'))
    progressBar.update(5, _("Discovery started"))
    
    complete = False
    while not progressBar.iscanceled() and not complete:

        progressBar.update(10, _("N-UPnP discovery..."))
        bridgeIP =_discoverNupnp()
        if not bridgeIP:
            progressBar.update(20, _("UPnP discovery..."))
            bridgeIP = _discoverSsdp()

        if connectionTest(bridgeIP):
            progressBar.update(100, _("Found bridge: ") + bridgeIP)
            monitor.waitForAbort(1)

            bridgeUser = createUser(monitor, bridgeIP, progressBar)
            
            if bridgeUser:
                logger.debug("User created: {}".format(bridgeUser))
                progressBar.update(90,_("User Found!"),_("Saving settings"))

                globals.ADDON.setSettingString("bridgeIP",bridgeIP)
                globals.ADDON.setSettingString("bridgeUser",bridgeUser)
                complete = True
                globals.connected = True
                progressBar.update(100, _("Complete!"))
                monitor.waitForAbort(5)
                progressBar.close()
                logger.debug("Bridge discovery complete")
                return True
            else:
                logger.debug("User not created, received: {}".format(bridgeUser))
                progressBar.update(100, _("User not found"),_("Check your bridge and network"))
                monitor.waitForAbort(5)
                complete = True

                progressBar.close()

        else:
            progressBar.update(100, _("Bridge not found"),_("Check your bridge and network"))
            logger.debug("Bridge not found, check your bridge and network")
            monitor.waitForAbort(5)
            complete = True
            progressBar.close()

    if progressBar.iscanceled():
        logger.debug("Bridge discovery cancelled by user")
        progressBar.update(100,_("Cancelled"))
        complete = True
        progressBar.close()


def connectionTest(bridgeIP):
    logger.debug("Connection Test IP: {}".format(bridgeIP))
    b = qhue.qhue.Resource("http://{}/api".format(bridgeIP))
    try:
        apiversion = b.config()['apiversion']
    except (requests.exceptions.ConnectionError, qhue.QhueException) as error:
        logger.debug("Connection test failed.  {}".format(error))
        return False

#TODO: compare API version properly, ensure api version >= 1.28
    if apiversion:
        logger.info("Bridge Found! Hue API version: {}".format(apiversion))
        return True
    logger.debug("in ConnectionTest():  Connected! Bridge too old: {}".format(apiversion))
    notification(_("Hue Service"), _("Bridge API: {}, update your bridge".format(apiversion)), icon=xbmcgui.NOTIFICATION_ERROR)
    return False


def userTest(bridgeIP,bridgeUser):
    logger.debug("in ConnectionTest() Attempt initial connection")
    b = qhue.Bridge(bridgeIP,bridgeUser,timeout=globals.QHUE_TIMEOUT)
    try:
        zigbeechan = b.config()['zigbeechannel']
    except (requests.exceptions.ConnectionError, qhue.QhueException):
        return False

    if zigbeechan:
        logger.info("Hue User Authorized. Bridge Zigbee Channel: {}".format(zigbeechan))
        return True
    return False


def discoverBridgeIP(monitor):
    #discover hue bridge IP silently for non-interactive discovery / bridge IP change.
    logger.debug("In discoverBridgeIP")
    bridgeIP = _discoverNupnp()
    if connectionTest(bridgeIP):
        return bridgeIP

    bridgeIP = _discoverSsdp()
    if connectionTest(bridgeIP):
        return bridgeIP
    
    return False




def createUser(monitor, bridgeIP, progressBar=False):
    logger.debug("In createUser")
    #device = 'kodi#'+getfqdn()
    data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn()) #Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

    req = requests
    res = 'link button not pressed'
    timeout = 0
    progress=0
    if progressBar:        
        progressBar.update(progress,_("Press link button on bridge"),_("Waiting for 90 seconds...")) #press link button on bridge


    while 'link button not pressed' in res and timeout <= 90  and not monitor.abortRequested() and not progressBar.iscanceled():
        logger.debug("In create_user: abortRquested: {}, timer: {}".format(str(monitor.abortRequested()),timeout) )

        if progressBar:
            progressBar.update(progress,_("Press link button on bridge")) #press link button on bridge


        req = requests.post('http://{}/api'.format(bridgeIP), data=data)
        res = req.text
        monitor.waitForAbort(1)
        timeout = timeout + 1
        progress = progress + 1

    res = req.json()
    logger.debug("json response: {}, content: {}".format(res,req.content))

    try:
        username = res[0]['success']['username']
        return username
    except Exception:
        logger.exception("Username exception")
        return False




def configureScene(bridge,kGroupID,action):
    scene=selectHueScene(bridge)
    if scene is not None:
        #group0_startSceneID
        globals.ADDON.setSettingString("group{}_{}SceneID".format(kGroupID, action),scene[0])
        globals.ADDON.setSettingString("group{}_{}SceneName".format(kGroupID,action), scene[1])
        globals.ADDON.openSettings()


def configureAmbiLights(bridge,kGroupID):
    lights=selectHueLights(bridge)
    lightNames = []
    colorLights=[]
    if lights is not None:
        for L in lights:
            #gamut = getLightGamut(bridge, L)
            #if gamut == "A" or gamut== "B" or gamut == "C": #defaults to C if unknown model
            lightNames.append(_getLightName(bridge,L))
            colorLights.append(L)

        globals.ADDON.setSettingString("group{}_Lights".format(kGroupID),','.join(colorLights))
        globals.ADDON.setSettingString("group{}_LightNames".format(kGroupID),','.join(lightNames))
        globals.ADDON.openSettings()


def _getLightName(bridge,L):
    try:
        name = bridge.lights()[L]['name']
    except Exception:
        logger.exception("getLightName Exception")
        return None
    
    if name is None:
        return None
    return name



def selectHueLights(bridge):
    logger.debug("In selectHueLights{}")
    hueLights=bridge.lights()

    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    items=[]
    index=[]
    lightIDs=[]
    
    for light in hueLights:

        hLight=hueLights[light]
        hLightName=hLight['name']
        
        #logger.debug("In selectHueGroup: {}, {}".format(hgroup,name))
        index.append(light)
        items.append(xbmcgui.ListItem(label=hLightName))
        
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    selected = xbmcgui.Dialog().multiselect(_("Select Hue Lights..."),items)
    if selected:
        #id = index[selected]
        for s in selected:
            lightIDs.append(index[s])

    logger.debug("lightIDs: {}".format(lightIDs))
    
    if lightIDs:
        return lightIDs
    return None




def selectHueScene(bridge):
    logger.debug("In selectHueScene{}")
    hueScenes=bridge.scenes()
    
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    items=[]
    index=[]
    selectedId = -1
    
    for scene in hueScenes:

        hScene=hueScenes[scene]
        hSceneName=hScene['name']

        if hScene['version'] == 2 and hScene["recycle"] is False and hScene["type"] == "LightScene":
            index.append(scene)
            items.append(xbmcgui.ListItem(label=hSceneName))

    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    selected = xbmcgui.Dialog().select("Select Hue scene...",items)
    if selected > -1 :
        selectedId = index[selected]
        hSceneName=hueScenes[selectedId]['name']
        logger.debug("In selectHueScene: selected: {}".format(selected))

    if selected > -1:
        return selectedId, hSceneName
    return None


def getDaylight(bridge):
    return bridge.sensors['1']()['state']['daylight']


def sunset(bridge,kgroups,ambiGroup):
    logger.info("Applying sunset scenes")

    for g in kgroups:
        logger.debug("in sunset() g: {}, kgroupID: {}".format(g,g.kgroupID))
        if globals.ADDON.getSettingBool("group{}_enabled".format(g.kgroupID)):
            g.sunset()
    if globals.ADDON.getSettingBool("group3_enabled"):
        ambiGroup.sunset()
    return


def connectBridge(monitor,silent=False):
    bridgeIP = globals.ADDON.getSettingString("bridgeIP")
    bridgeUser = globals.ADDON.getSettingString("bridgeUser")
    logger.debug("in Connect() with settings: bridgeIP: {}, bridgeUser: {}".format(bridgeIP,bridgeUser))

    if bridgeIP and bridgeUser:
        if connectionTest(bridgeIP):
            logger.debug("in Connect(): Bridge responding to connection test.")
        else:
            logger.debug("in Connect(): Bridge not responding to connection test, attempt finding a new bridge IP.")
            bridgeIP = discoverBridgeIP(monitor)
            if bridgeIP:
                logger.debug("in Connect(): New IP found: {}. Saving".format(bridgeIP))
                globals.ADDON.setSettingString("bridgeIP",bridgeIP)

        if bridgeIP:
            logger.debug("in Connect(): Checking User")
            if userTest(bridgeIP, bridgeUser):
                bridge = qhue.Bridge(bridgeIP,bridgeUser,timeout=globals.QHUE_TIMEOUT)
                globals.connected = True
                logger.info("Successfully connected to Hue Bridge: {}".format(bridgeIP))
                if not silent:
                    notification(_("Hue Service"), _("Hue connected"), icon=xbmcgui.NOTIFICATION_INFO)
                return bridge
        else: 
            logger.debug("Bridge not responding")
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            globals.connected = False
            return None

    else:
        logger.debug("Bridge not configured")
        notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)
        globals.connected = False
        return None


def validateSchedule():
    logger.debug("Validate schedule. Schedule Enabled: {}".format(globals.enableSchedule))
    if globals.enableSchedule:
        try:
            convertTime(globals.startTime)
            convertTime(globals.endTime)
            logger.debug("Time looks valid")
        except ValueError as e:
            logger.error("Invalid time settings: {}".format(e))
            notification(_("Hue Service"), _("Invalid start or end time, schedule disabled"), icon=xbmcgui.NOTIFICATION_ERROR)
            globals.ADDON.setSettingBool("EnableSchedule", False)
            globals.enableSchedule = False


def getLightGamut(bridge,L):
    try:
        gamut = bridge.lights()[L]['capabilities']['control']['colorgamuttype']
        logger.debug("Light: {}, gamut: {}".format(L,gamut))
    except Exception:
        logger.exception("Can't get gamut for light, defaulting to Gamut C: {}".format(L))
        return "C"
    if gamut == "A"  or gamut == "B" or gamut == "C":
        return gamut
    return "C" #default to C if unknown gamut type



def checkBridgeModel(bridge):
    try:
        bridgeConfig = bridge.config()
        model=bridgeConfig["modelid"]
    except QhueException:
        logger.exception("Exception: checkBridgeModel")
        return None
    if model == "BSB002":
        logger.debug("Bridge model OK: {}".format(model))
        return True
    logger.error("Unsupported bridge model: {}".format(model))
    xbmcgui.Dialog().ok(_("Unsupported Hue Bridge"),_("Hue Bridge V1 (Round) is unsupported. Hue Bridge V2 (Square) is required for certain features."))
    return None


def convertTime(time):
    hour=int(time.split(":")[0])
    minute=int(time.split(":")[1])
    return datetime.time(hour,minute)

def notification(header, message, time=5000, icon=globals.ADDON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)

def perfAverage(processTimes):
    processTimes=list(processTimes) #deque is mutating during iteration for some reason, so copy to list.
    size=len(processTimes)
    total = 0
    for x in processTimes: 
        total += x
    averageProcessTime=int(total/size * 1000)
    return "{} ms".format(averageProcessTime)


class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super(xbmc.Monitor,self).__init__()

    def onSettingsChanged(self):
        logger.info("Settings changed")
        #self.waitForAbort(1)
        loadSettings()
        globals.settingsChanged = True
