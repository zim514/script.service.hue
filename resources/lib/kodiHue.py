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

import kodiutils
import qhue, tools
#from resources.lib.qhue import qhue,QhueException,Bridge
from qhue import Bridge

from kodiutils import notification, get_string




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





def setup(monitor, notify=True):
    #Force full setup, ignore any existing settings. This may create a duplicate user as Hue API doesn't prevent multiple users with same Devicetype
    logger.debug("Kodi Hue: In kodiHue setup(mon)")
    
    bridgeIP = ""
    bridgeUser = ""
    #bridgeIP = kodiutils.get_setting("bridgeIp")
    #bridgeUser = kodiutils.get_setting("bridgeUser")
    
    
    
    bridgeIP = discoverBridgeIP(monitor)
    if bridgeIP:
        logger.debug("Kodi Hue: In setup(), bridge found: {}".format(bridgeIP))
        notification("Kodi Hue", "Bridge found, creating user. IP: {}".format(bridgeIP), time=5000, icon=ADDON.getAddonInfo('icon'), sound=False)       
        bridgeUser = create_user(monitor, bridgeIP, notify=True)
        
        if bridgeUser:
            logger.debug("Kodi Hue: In setup(), user created: {}".format(bridgeUser))
            notification("Kodi Hue", "Bridge configured", time=5000, icon=ADDON.getAddonInfo('icon'), sound=False)
            kodiutils.set_setting("bridgeIP", bridgeIP)
            kodiutils.set_setting("bridgeUser", bridgeUser)
        else:
            logger.debug("Kodi Hue: In setup(), create user returned nothing")
        
    else:
        logger.debug("Kodi Hue: In setup(), bridge discovery returned nothing")
        notification("Kodi Hue", "Could not find bridge. Check settings", time=5000, icon=ADDON.getAddonInfo('icon'), sound=True)

    return
            
        
        
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



class KodiPlayer(xbmc.Player):
    duration = 0
    playingvideo = False
    playlistlen = 0
    movie = False

    def __init__(self):
        logger.debug('Kodi Hue: In MyPlayer.__init__()')
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        logger.debug('Kodi Hue: In MyPlayer.onPlayBackStarted()')
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playlistlen = playlist.size()
        self.playlistpos = playlist.getposition()
        self.playingvideo = True
        self.duration = self.getTotalTime()
        #state_changed("started", self.duration)

    def onPlayBackPaused(self):
        logger.debug('Kodi Hue: In MyPlayer.onPlayBackPaused()')
        #state_changed("paused", self.duration)
        if self.isPlayingVideo():
            self.playingvideo = False

    def onPlayBackResumed(self):
        logger.debug('Kodi Hue: In MyPlayer.onPlayBackResume()')
        #state_changed("resumed", self.duration)
        if self.isPlayingVideo():
            self.playingvideo = True
            if self.duration == 0:
                self.duration = self.getTotalTime()

    def onPlayBackStopped(self):
        logger.debug('Kodi Hue: In MyPlayer.onPlayBackStopped()')
        #state_changed("stopped", self.duration)
        self.playingvideo = False
        self.playlistlen = 0

    def onPlayBackEnded(self):
        logger.debug('Kodi Hue: In MyPlayer.onPlayBackEnded()')
        # If there are upcoming plays, ignore
        if self.playlistpos < self.playlistlen-1:
            return

        self.playingvideo = False
        #state_changed("stopped", self.duration)
        
        

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




def initialConnect(monitor,discover=False,silent=False):
    global connected
    if discover:
        logger.debug("Kodi Hue: Discovery selected, don't load existing bridge settings.")
    else:
        bridgeIP = kodiutils.get_setting("bridgeIP")
        bridgeUser = kodiutils.get_setting("bridgeUser")
        connected = False

    logger.debug("Kodi Hue: in initialConnect() with settings: bridgeIP: {}, bridgeUser: {}, discovery: {}".format(bridgeIP,bridgeUser,discover))

    
    if bridgeIP and bridgeUser:
        if userTest(bridgeIP, bridgeUser):
            bridge = qhue.Bridge(bridgeIP,bridgeUser)
            connected = True
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
    

    