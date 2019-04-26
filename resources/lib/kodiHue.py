'''
Created on Apr. 12, 2019

@author: zim514
'''
import sys
import logging
import requests
from socket import getfqdn

import globals

import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import NOTIFICATION_ERROR,NOTIFICATION_WARNING, NOTIFICATION_INFO
import globals
import kodiutils
from KodiGroup import KodiGroup

from kodiutils import notification, get_string




from resources.lib import globals
from resources.lib.qhue import qhue,QhueException,Bridge


ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))


def _discoverNupnp():
    logger.debug("Kodi Hue: In kodiHue discover_nupnp()")
  
    req = requests.get('https://discovery.meethue.com/')
    res = req.json()
    bridge_ip = None
    if res:
        bridge_ip = res[0]["internalipaddress"]

    return bridge_ip
        
        
def bridgeDiscover(monitor):
    logger.debug("Kodi Hue: In bridgeDiscover:")
    #Create new config if none exists. Returns success or fail as bool
    kodiutils.set_setting("bridgeIP","")
    kodiutils.set_setting("bridgeUser","")
    globals.connected = False
    
    
    progressBar = xbmcgui.DialogProgress()
    progressBar.create('Discover bridge...')
    progressBar.update(5, "Discovery started")
    
    complete = False
    while not progressBar.iscanceled() and not complete:

#TODO: ADD DISCOVERY METHODS in their own method with progress bar support (or not) and support for initial connect        
        #bridgeIP = discoverBridgeIP..
        progressBar.update(10, "nupnp discovery... ")
        bridgeIP =_discoverNupnp()
        
        if connectionTest(bridgeIP):
            progressBar.update(100, "Found bridge: " + bridgeIP)
            xbmc.sleep(1000)
                     
            bridgeUser = createUser(monitor, bridgeIP, progressBar)
            if bridgeUser:
                progressBar.update(90,"User Found!","Saving settings")
                
                kodiutils.set_setting("bridgeIP",bridgeIP)
                kodiutils.set_setting("bridgeUser",bridgeUser)
                complete = True
                progressBar.update(100, "Complete!")
                monitor.waitForAbort(5)
                progressBar.close()
            else:
                progressBar.update(100, "User not found","Check your bridge and network")
                monitor.waitForAbort(5)
                complete = True
           
                progressBar.close()
            
        else:
            progressBar.update(100, "Bridge not found","Check your bridge and network")
            monitor.waitForAbort(5)
            complete = True
            progressBar.close()

    if progressBar.iscanceled():
        progressBar.update(100,"Cancelled")
        complete = True
        progressBar.close()
        
       
def connectionTest(bridgeIP):
    logger.debug("Kodi Hue: in ConnectionTest() Attempt initial connection")
    b = qhue.Resource("http://{}/api".format(bridgeIP))
    try:
        test = b.config()['apiversion']
    except:
        return False
    
    if test:
        logger.debug("Kodi Hue: in ConnectionTest():  Connected! Test Value: {}".format(test))
        return True
    else:
        return False


def userTest(bridgeIP,bridgeUser):
    logger.debug("Kodi Hue: in ConnectionTest() Attempt initial connection")
    b = Bridge(bridgeIP,bridgeUser)
    try:
        zigbeechan = b.config()['zigbeechannel']
    except:
        return False
    
    if zigbeechan:
        logger.debug("Kodi Hue: in userTest():  Authorized! Bridge Zigbee Channel: {}".format(zigbeechan))
        return True
    else:
        return False                                       

    
        
def discoverBridgeIP(monitor):
    #discover hue bridge
    logger.debug("Kodi Hue: In discoverBridgeIP")
    #TODO: implement upnp discovery
    #bridge_ip = _discover_upnp()  
    bridgeIP = None
    if bridgeIP is None:
        bridgeIP = _discoverNupnp()
    
    if connectionTest(bridgeIP):
        return bridgeIP
    else:
        return False

       

def createUser(monitor, bridgeIP, progressBar=False):
    #device = 'kodi#'+getfqdn()
    data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn()) #Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

    req = requests
    res = 'link button not pressed'
    timeout = 0
    progress=0
    if progressBar:        
        progressBar.update(progress,get_string(9001),"Waiting for 90 seconds...") #press link button on bridge
    
    
    while 'link button not pressed' in res and timeout <= 90  and not monitor.abortRequested() and not progressBar.iscanceled():
        logger.debug("Kodi Hue: In create_user: abortRquested: {}, timer: {}".format(str(monitor.abortRequested()),timeout) )
        
        if progressBar:
            progressBar.update(progress,get_string(9001)) #press link button on bridge
             #notification(get_string(9000), get_string(9001), time=1000, icon=xbmcgui.NOTIFICATION_WARNING) #9002: Press link button on bridge
            
        req = requests.post('http://{}/api'.format(bridgeIP), data=data)
        res = req.text
        monitor.waitForAbort(1)
        timeout = timeout + 1
        progress = progress + 1

    res = req.json()
    
    try:
        username = res[0]['success']['username']
        return username
    except:
        return False


def configureGroup(bridge,kGroupID):
    hGroup=selectHueGroup(bridge)
    kodiutils.set_setting("group{}_hGroupID".format(kGroupID), hGroup[0])
    kodiutils.set_setting("group{}_hGroupName".format(kGroupID), hGroup[1])
    ADDON.openSettings()


def selectHueGroup(bridge):
    logger.debug("Kodi Hue: In selectHueGroup{}")
    hueGroups=bridge.groups()
    
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    items=[]
    index=[]
    
    index.append(0)
    items.append(xbmcgui.ListItem(label="All lights"))
    for group in hueGroups:

        hGroup=hueGroups[group]
        hGroupName=hGroup['name']
        
        #logger.debug("Kodi Hue: In selectHueGroup: {}, {}".format(hgroup,name))
        index.append(group)
        items.append(xbmcgui.ListItem(label=hGroupName))
        
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    selected = xbmcgui.Dialog().select("Select Hue group...",items)
    
    id = index[selected]
    hGroupName=hueGroups[id]['name']
    logger.debug("Kodi Hue: In selectHueGroup: selected: {}".format(selected))
    
    if id:
        return id, hGroupName;
    else:
        return None


def getDaylight(bridge):
    sensors = bridge.sensors()
    return bridge.sensors['1']()['state']['daylight']
            

def setupGroups(bridge):
    logger.debug("Kodi Hue: in setupGroups()")
    kgroups= []   
    g=0
    while g < globals.NUM_GROUPS:
        if kodiutils.get_setting_as_bool("group{}_enabled".format(g)):
            kgroups.append(KodiGroup())
            kgroups[g].setup(bridge, g, kodiutils.get_setting_as_int("group{}_hGroupID".format(g))) 
        g = g + 1
        
    return kgroups

                   


def connectBridge(monitor,silent=False):
    bridgeIP = kodiutils.get_setting("bridgeIP")
    bridgeUser = kodiutils.get_setting("bridgeUser")
    logger.debug("Kodi Hue: in Connect() with settings: bridgeIP: {}, bridgeUser: {}".format(bridgeIP,bridgeUser))

    
    if bridgeIP and bridgeUser:
        if connectionTest(bridgeIP):
            logger.debug("Kodi Hue: in Connect(): Bridge responding to connection test.")

        else:
            logger.debug("Kodi Hue: in Connect(): Bridge not responding to connection test, attempt finding a new bridge IP.")
            bridgeIP = discoverBridgeIP(monitor)
            if bridgeIP:
                logger.debug("Kodi Hue: in Connect(): New IP found: {}. Saving".format(bridgeIP))
                kodiutils.set_setting("bridgeIP",bridgeIP)
                        
        
        if bridgeIP:
            logger.debug("Kodi Hue: in Connect(): Checking User")
            if userTest(bridgeIP, bridgeUser):
                bridge = qhue.Bridge(bridgeIP,bridgeUser)
                globals.connected = True
                logger.debug("Kodi Hue: Connected!")
                if not silent:
                    kodiutils.notification("Kodi Hue", "Hue connected", icon=NOTIFICATION_INFO)
                return bridge
        else: 
            logger.debug("Kodi Hue: Bridge not responding")
            kodiutils.notification("Kodi Hue", "Bridge connection failed", icon=NOTIFICATION_ERROR)
            globals.connected = False
            return False
            
         
            
    else:
        logger.debug("Kodi Hue: Bridge not configured")
        kodiutils.notification("Kodi Hue", "Bridge not configured", icon=NOTIFICATION_ERROR)
        globals.connected = False
        return False
    
    
class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super(xbmc.Monitor,self).__init__()
        
    def onSettingsChanged(self):
        logger.debug("Kodi Hue: Settings changed")
        globals.settingsChanged = True
