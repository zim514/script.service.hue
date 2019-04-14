'''
Created on Apr. 12, 2019

@author: zim514
'''
import logging
import requests
from socket import getfqdn


import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import kodiutils
from resources.lib import qhue, tools
from resources.lib.qhue import qhue,QhueException,Bridge

#from resources.lib.qhue import Bridge

from resources.lib.kodiutils import notification, get_string


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
    
    
    
    bridgeIP = discover(monitor)
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
            
        
        
        
    
        
def discover(monitor):
    #discover hue bridge
    logger.debug("Kodi Hue: In kodiHue discover()")
    #TODO: implement upnp discovery
    #bridge_ip = _discover_upnp()  
    bridge_ip = None
    if bridge_ip is None:
        bridge_ip = discover_nupnp()
    return bridge_ip

def connect(monitor,autodiscover=True,notify=True,):
    bridgeIP = kodiutils.get_setting("bridgeIp")
    bridgeUser = kodiutils.get_setting("bridgeUser")
        
    if not bridgeIP:
        logger.debug("Kodi Hue: No bridge IP set, calling KodiHue.discover()")
        notification("Kodi Hue", "Bridge not configured. Starting discovery", time=5000, icon=ADDON.getAddonInfo('icon'), sound=True)
        bridgeIP=discover(monitor)
        notification("Kodi Hue", "Bridge found, creating user. IP: {}".format(bridgeIP), time=5000, icon=ADDON.getAddonInfo('icon'), sound=True)
        logger.debug("Kodi Hue: Bridge found, creating user. IP: {}".format(bridgeIP))
        bridgeUser = create_user(bridgeIP, True)
        #if bridgeIP and bridgeUser:
            #if bridge setup worked, save settings
            #TODO: catch errors....
            #kodiutils.set_setting("bridgeIP", bridgeIP)
            #kodiutils.set_setting("bridgeUser", bridgeUser)

    logger.debug("Kodi Hue: Bridge setup. IP: " + str(bridgeIP) + " User: " + str(bridgeUser))
    return "unimplemented"    
    
        # create the bridge resource, passing the captured username
    
    bridge = Bridge(bridgeIP, bridgeUser)
    
    # create a lights resource
    lights = bridge.lights

    # query the API and print the results
    logger.debug("Kodi Hue: Qhue.Bridge" + str(bridge()))
    logger.debug("Kodi Hue: Qhue.Lights" + str(lights()))
    
    
    return 


def create_user(monitor, bridge_ip, notify=True):
    #device = 'kodi#'+getfqdn()
    data = '{{"devicetype": "kodi#{}"}}'.format(getfqdn()) #Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

    res = 'link button not pressed'
    timeout = 0
    while 'link button not pressed' in res and not monitor.abortRequested() and timeout <= 15   :
        logger.debug("Kodi Hue: In create_user: abortRquested: {}, timer: {}".format(str(monitor.abortRequested()),timeout) )
        req = requests.post('http://{}/api'.format(bridge_ip), data=data)
        res = req.text
        if notify:
            notification(get_string(9000), get_string(9001), time=1000, icon=xbmcgui.NOTIFICATION_WARNING, sound=True) #9002: Press link button on bridge
        xbmc.sleep(1000)
        timeout = timeout + 1

    res = req.json()
    
    try:
        username = res[0]['success']['username']
        return username
    except:
        return False


    

def create_user2(mon,bridge_ip, notify=True):
    devicetype = "kodi#" + getfqdn()
#    data = '{{"devicetype": "{}"}}'.format(devicetype)

    res = 'link button not pressed' #string returned by Hue bridge while button needs to be pressed. 
    b = qhue.Resource("http://{}/api'".format(bridge_ip))
    
    while 'link button not pressed' in res and not mon.abortRequested(): #check for button press every second until app abort. 
        if notify:
            notification(get_string(9000), get_string(9001), time=5000, icon=ADDON.getAddonInfo('icon'), sound=False) 
            #String 9001: Press bridge button to connect
        
        logger.debug("Kodi Hue: create_user2: b: {},devicetype: {}".format(str(b),str(devicetype)))
        try:
            res = b(devicetype=devicetype, http_method="post")
        except:
            logger.debug("Kodi Hue: create_user2 loop: " + (str(res)))
            xbmc.sleep(5000)
            pass
    
    response = res[0]["success"]["username"]
    logger.debug("Kodi Hue: create_user2: wait... did this work? "  + str(response)) 
  #  response = res(devicetype=devicetype, http_method="post")
    return response



    