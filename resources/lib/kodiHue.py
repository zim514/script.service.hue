'''
Created on Apr. 12, 2019

@author: zim514
'''
import sys
import logging
import requests
from socket import getfqdn


import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import NOTIFICATION_ERROR,NOTIFICATION_WARNING, NOTIFICATION_INFO
import globals
import kodiutils
#import KodiGroup
from KodiGroup import KodiGroup
#import  tools

from kodiutils import notification, get_string
from resources.lib.globals import NUM_GROUPS



from resources.lib import globals
from resources.lib.qhue import qhue,QhueException,Bridge


ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))


def discover_nupnp():
    logger.debug("Kodi Hue: In kodiHue discover_nupnp()")
  
    req = requests.get('https://discovery.meethue.com/')
    res = req.json()
    bridge_ip = None
    if res:
        bridge_ip = res[0]["internalipaddress"]

    return bridge_ip
        
        
def initialSetup(monitor):
    #Create new config if none exists. Returns success or fail as bool
    bridgeIP = kodiutils.get_setting("bridgeIP")
    bridgeUser = kodiutils.get_setting("bridgeUser")
    
    logger.debug("Kodi Hue: In InitialSetup:  Hue settings read: Bridge IP: {},Bridge User: {}".format(bridgeIP,bridgeUser))
    
    if bridgeIP:
        #check if the saved IP is any good
        if connectionTest(bridgeIP): 
            #connection success! save IP again for good measure
            kodiutils.set_setting("BridgeIP", bridgeIP)
        else:
            #connection failed, flush IP
            bridgeIP = ""
            kodiutils.set_setting("BridgeIP", bridgeIP)
            
    if not bridgeIP:
        #IP is no good, find a new one.
        bridgeIP = discoverBridgeIP(monitor)
        if connectionTest(bridgeIP): 
            #this IP is legit, save it.
            kodiutils.set_setting("BridgeIP", bridgeIP)
        else:
            #this IP is still no good. Give up
            return False
            
######        
    if bridgeUser:
        #a user is set, check if OK.
        if userTest(bridgeIP, bridgeUser):
            #I have a user and its valid! save it again for good measure.
            kodiutils.set_setting("BridgeUser", bridgeUser)
        else:
            #configured user is unauthorized, delete it.
            bridgeUser = ""
            kodiutils.set_setting("BridgeUser", bridgeUser)
    
    
    if not bridgeUser:
        #STILL no legit user, create a new one.
        bridgeUser = create_user(monitor, bridgeIP, notify=True)
        if bridgeUser:
            #user seems good, save
            kodiutils.set_setting("BridgeUser", bridgeUser)
        else:
            #no user found, give up
            return False
    #everything seems ok so return a Bridge
    return Bridge(bridgeIP,bridgeUser)

       
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
    logger.debug("Kodi Hue: In kodiHue discover()")
    #TODO: implement upnp discovery
    #bridge_ip = _discover_upnp()  
    bridgeIP = None
    if bridgeIP is None:
        bridgeIP = discover_nupnp()
    
    if connectionTest(bridgeIP):
        return bridgeIP
    else:
        return False

       

def create_user(monitor, bridgeIP, notify=True):
    #device = 'kodi#'+getfqdn()
    data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn()) #Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

    res = 'link button not pressed'
    timeout = 0
    while 'link button not pressed' in res and not monitor.abortRequested() and timeout <= 15   :
        logger.debug("Kodi Hue: In create_user: abortRquested: {}, timer: {}".format(str(monitor.abortRequested()),timeout) )
        if notify:
            notification(get_string(9000), get_string(9001), time=1000, icon=xbmcgui.NOTIFICATION_WARNING, sound=True) #9002: Press link button on bridge
        req = requests.post('http://{}/api'.format(bridgeIP), data=data)
        res = req.text
        xbmc.sleep(1000)
        timeout = timeout + 1

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
            

def reloadGroups(bridge,kgroups):
    logger.debug("Kodi Hue: reloadGroups()")
    del kgroups
    kgroups = [] 
    
       
    g=0
    while g < NUM_GROUPS:
        
        kgroups.append(KodiGroup())
        kgroups[g].setup(bridge, g, kodiutils.get_setting_as_int("group{}_hGroupID".format(g))) 
        g = g + 1
    
    return kgroups

                   


def initialConnect(monitor,discover=False,silent=False):
    
    if discover:
        logger.debug("Kodi Hue: Discovery selected, don't load existing bridge settings.")
    else:
        bridgeIP = kodiutils.get_setting("bridgeIP")
        bridgeUser = kodiutils.get_setting("bridgeUser")
        globals.connected = False

    logger.debug("Kodi Hue: in initialConnect() with settings: bridgeIP: {}, bridgeUser: {}, discovery: {}".format(bridgeIP,bridgeUser,discover))

    
    if bridgeIP and bridgeUser:
        if userTest(bridgeIP, bridgeUser):
            bridge = qhue.Bridge(bridgeIP,bridgeUser)
            globals.connected = True
            if not silent:
                kodiutils.notification("Kodi Hue", "Bridge connected", time=5000, icon=NOTIFICATION_INFO, sound=False)
            logger.debug("Kodi Hue: Connected!")
            return bridge
     
        else:
            bridge = initialSetup(monitor)
            if not bridge:
                logger.debug("Kodi Hue: Connection failed, exiting script")
                kodiutils.notification("Kodi Hue", "Bridge not found", time=5000, icon=NOTIFICATION_ERROR, sound=True)
                return #return nothing
        
    else:
        bridge = initialSetup(monitor)    
        if not bridge:
            logger.debug("Kodi Hue: Connection failed, exiting script")
            kodiutils.notification("Kodi Hue", "Bridge not found", time=5000, icon=NOTIFICATION_ERROR, sound=True)
            return 
    
    
class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super(xbmc.Monitor,self).__init__()
        
    def onSettingsChanged(self):
        logger.debug("Kodi Hue: Settings changed")
        globals.settingsChanged = True
