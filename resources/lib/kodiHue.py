'''
Created on Apr. 12, 2019

@author: zim514
'''
import logging
import requests
from socket import getfqdn


import xbmc
import xbmcaddon

from resources.lib import kodiutils
from resources.lib import qhue, tools
from resources.lib.qhue import qhue,QhueException,Bridge

from resources.lib.kodiutils import notification, get_string


def discover_nupnp():
    logger.debug("Kodi Hue: In kodiHue discover_nupnp()")
  
    req = requests.get('https://discovery.meethue.com/')
    res = req.json()
    bridge_ip = None
    if res:
        bridge_ip = res[0]["internalipaddress"]

    return bridge_ip



#from resources.lib.qhue import Bridge

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))

        
def discover(mon):
    #discover hue bridge
    logger.debug("Kodi Hue: In kodiHue discover()")
    #TODO: implement upnp discovery
    #bridge_ip = _discover_upnp()  
    bridge_ip = None
    if bridge_ip is None:
        bridge_ip = discover_nupnp()
    return bridge_ip


def create_user(mon,bridge_ip, notify=True):
    devicetype = "kodi#" + getfqdn()
#    data = '{{"devicetype": "{}"}}'.format(devicetype)

    res = 'link button not pressed' #string returned by Hue bridge while button needs to be pressed. 
    
    
    while 'link button not pressed' in res and not mon.abortRequested(): #check for button press every second forever. 
        if notify:
            notification(get_string(9000), get_string(9001), time=5000, icon=ADDON.getAddonInfo('icon'), sound=False) 
            #String 9001: Press bridge button to connect
        b = qhue.Resource("http://{}/api'".format(bridge_ip))
#        logger.debug("Kodi Hue: create_user: b: {},devicetype: {}".format(str(b),str(devicetype)))
        try:
            res = b(devicetype=devicetype, http_method="post")
        except:
            logger.debug("Kodi Hue: create_user loop: " + (str(res)))
            xbmc.sleep(5000)
            pass
    
    
  #  response = res(devicetype=devicetype, http_method="post")
    return res[0]["success"]["username"]



    