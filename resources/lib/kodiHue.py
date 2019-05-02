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
logger = logging.getLogger(__name__)

def createHueGroup(bridge):
    logger.debug("In kodiHue createHueGroup")
    groupName = xbmcgui.Dialog().input("Group Name")
    if groupName:              
        selected = selectHueLights(bridge)
        if selected:
            groups=bridge.groups
            res=groups(lights=selected,name=groupName,http_method='post')
            logger.debug("In kodiHue createHueGroup. Res:".format(res))
            if res[0]["success"]:
                xbmcgui.Dialog().notification("Hue", "Group Created")
            else:
                xbmcgui.Dialog().notification("Hue", "ERROR: Group not created")
                 
def deleteHueGroup(bridge):
    logger.debug("In kodiHue deleteHueGroup")
    group = selectHueGroup(bridge)
    if group:
        confirm = xbmcgui.Dialog().yesno("Delete Hue Group", "Are you sure you want to delete this group: ", unicode(group[1]))
    if group and confirm:              
        groups=bridge.groups
        res=groups[group[0]](http_method='delete')
        logger.debug("In kodiHue createHueGroup. Res:".format(res))
        if res[0]["success"]:
            xbmcgui.Dialog().notification("Hue", "Group deleted")
        else:
            xbmcgui.Dialog().notification("Hue", "ERROR: Group not created")

            
        
    

def _discoverNupnp():
    logger.debug("In kodiHue discover_nupnp()")
  
    req = requests.get('https://discovery.meethue.com/')
    res = req.json()
    bridge_ip = None
    if res:
        bridge_ip = res[0]["internalipaddress"]

    return bridge_ip
        
        
def bridgeDiscover(monitor):
    logger.debug("In bridgeDiscover:")
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
    logger.debug("in ConnectionTest() Attempt initial connection")
    b = qhue.Resource("http://{}/api".format(bridgeIP))
    try:
        test = b.config()['apiversion']
    except:
        return False
    
    if test:
        logger.debug("in ConnectionTest():  Connected! Test Value: {}".format(test))
        return True
    else:
        return False


def userTest(bridgeIP,bridgeUser):
    logger.debug("in ConnectionTest() Attempt initial connection")
    b = Bridge(bridgeIP,bridgeUser)
    try:
        zigbeechan = b.config()['zigbeechannel']
    except:
        return False
    
    if zigbeechan:
        logger.debug("in userTest():  Authorized! Bridge Zigbee Channel: {}".format(zigbeechan))
        return True
    else:
        return False                                       

    
        
def discoverBridgeIP(monitor):
    #discover hue bridge
    logger.debug("In discoverBridgeIP")
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
        logger.debug("In create_user: abortRquested: {}, timer: {}".format(str(monitor.abortRequested()),timeout) )
        
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
    if hGroup > 0:
        kodiutils.set_setting("group{}_hGroupID".format(kGroupID), hGroup[0])
        kodiutils.set_setting("group{}_hGroupName".format(kGroupID), hGroup[1])
        ADDON.openSettings()



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
    selected = xbmcgui.Dialog().multiselect("Select Hue Lights...",items)
    if selected:
        #id = index[selected]
        for s in selected:
            lightIDs.append(index[s])
            
    
    logger.debug("In selectHueGroup: selected: {}".format(selected))
    
    if lightIDs:
        return lightIDs;
    else:
        return None    
    
    
    
    if selected:
        return selected
    else:
        return None



def selectHueGroup(bridge):
    logger.debug("In selectHueGroup{}")
    hueGroups=bridge.groups()
    
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    items=[]
    index=[]
    id = 0
    
#    index.append(0)
#    items.append(xbmcgui.ListItem(label="All lights"))
    for group in hueGroups:

        hGroup=hueGroups[group]
        hGroupName=hGroup['name']
        
        #logger.debug("In selectHueGroup: {}, {}".format(hgroup,name))
        index.append(group)
        items.append(xbmcgui.ListItem(label=hGroupName))
        
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    selected = xbmcgui.Dialog().select("Select Hue group...",items)
    if selected > 0 :
        id = index[selected]
        hGroupName=hueGroups[id]['name']
        logger.debug("In selectHueGroup: selected: {}".format(selected))
    
    if id:
        return id, hGroupName;
    else:
        return None


def getDaylight(bridge):
    logger.debug("in getDaylight()")
    sensors = bridge.sensors()
    return bridge.sensors['1']()['state']['daylight']
            

def sunset(bridge,kgroups):
    logger.debug("in sunset()")
    
    for g in kgroups:
        logger.debug("in sunset() g: {}, kgroupID: {}".format(g,g.kgroupID))
        if kodiutils.get_setting_as_bool("group{}_enabled".format(g.kgroupID)):
            g.sunset()
            
    return        
        
    
    

def setupGroups(bridge,flash=False):
    logger.debug("in setupGroups()")
    kgroups= []   
    g=0
    while g < globals.NUM_GROUPS:
        if kodiutils.get_setting_as_bool("group{}_enabled".format(g)):
            kgroups.append(KodiGroup())
            kgroups[g].setup(bridge, g, kodiutils.get_setting_as_int("group{}_hGroupID".format(g)), flash)  
        g = g + 1
        
    return kgroups

                   


def connectBridge(monitor,silent=False):
    bridgeIP = kodiutils.get_setting("bridgeIP")
    bridgeUser = kodiutils.get_setting("bridgeUser")
    logger.debug("in Connect() with settings: bridgeIP: {}, bridgeUser: {}".format(bridgeIP,bridgeUser))

    
    if bridgeIP and bridgeUser:
        if connectionTest(bridgeIP):
            logger.debug("in Connect(): Bridge responding to connection test.")

        else:
            logger.debug("in Connect(): Bridge not responding to connection test, attempt finding a new bridge IP.")
            bridgeIP = discoverBridgeIP(monitor)
            if bridgeIP:
                logger.debug("in Connect(): New IP found: {}. Saving".format(bridgeIP))
                kodiutils.set_setting("bridgeIP",bridgeIP)
                        
        
        if bridgeIP:
            logger.debug("in Connect(): Checking User")
            if userTest(bridgeIP, bridgeUser):
                bridge = qhue.Bridge(bridgeIP,bridgeUser)
                globals.connected = True
                logger.debug("Connected!")
                if not silent:
                    kodiutils.notification("Kodi Hue", "Hue connected", icon=NOTIFICATION_INFO)
                return bridge
        else: 
            logger.debug("Bridge not responding")
            kodiutils.notification("Kodi Hue", "Bridge connection failed", icon=NOTIFICATION_ERROR)
            globals.connected = False
            return False
            
         
            
    else:
        logger.debug("Bridge not configured")
        kodiutils.notification("Kodi Hue", "Bridge not configured", icon=NOTIFICATION_ERROR)
        globals.connected = False
        return False
    
    
class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super(xbmc.Monitor,self).__init__()
        
    def onSettingsChanged(self):
        logger.debug("Settings changed")
        globals.settingsChanged = True
