# -*- coding: utf-8 -*-

import sys
import logging
from threading import Event

import xbmc
import xbmcaddon
from xbmcgui import NOTIFICATION_ERROR,NOTIFICATION_WARNING, NOTIFICATION_INFO


from  resources.lib.qhue import Bridge
from resources.lib import kodiutils
from resources.lib import KodiGroup
from resources.lib import kodiHue                                                                                                                                                          



__addon__ = xbmcaddon.Addon()
__addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__cwd__ = __addon__.getAddonInfo('path')

from resources.lib.tools import get_version


ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))


logger.debug("Kodi Hue: In .(argv={}) service started, version: {}, SYSPATH: {}".format(
    sys.argv, get_version(), sys.path))

ev = Event()
capture = xbmc.RenderCapture()
fmt = capture.getImageFormat()
# BGRA or RGBA
fmtRGBA = fmt == 'RGBA'



##################################################
## RUN
###################
def run():
    logger.debug("Kodi Hue: In .(argv={}) service started, version: {}".format(
        sys.argv, get_version()))

    args = None
    if len(sys.argv) == 2:
        args = sys.argv[1]

    logger.debug("Kodi Hue: Args: {}".format(args))
    
    bridgeIP = ""
    bridgeUser = ""

    
    ev = Event()
    capture = xbmc.RenderCapture()
    fmt = capture.getImageFormat()
    # BGRA or RGBA
    fmtRGBA = fmt == 'RGBA'
    global connected
    connected = False
    
    
    #monitor = MyMonitor(settings)
    monitor=xbmc.Monitor()
    
    

    
###########################################################
########################################################### 
########################################################### 
###########################################################     

    if args == "discover":
        logger.debug("Kodi Hue: Discovery selected, don't load existing bridge settings.")
    else:
        bridgeIP = kodiutils.get_setting("bridgeIP")
        bridgeUser = kodiutils.get_setting("bridgeUser")

    logger.debug("Kodi Hue: Started with args: {}, bridgeIP: {}, bridgeUser: {}".format(args,bridgeIP,bridgeUser))

    
    if bridgeIP and bridgeUser:
        if kodiHue.userTest(bridgeIP, bridgeUser):
            bridge = Bridge(bridgeIP,bridgeUser)
            connected = True
            kodiutils.notification("Kodi Hue", "Bridge connected", time=5000, icon=NOTIFICATION_INFO, sound=True)
            logger.debug("Kodi Hue: Connected!")
     
        else:
            bridge = kodiHue.initialSetup(monitor)
            if not bridge:
                logger.debug("Kodi Hue: Connection failed, exiting script")
                kodiutils.notification("Kodi Hue", "Bridge not found, check your network", time=5000, icon=NOTIFICATION_ERROR, sound=True)
                return #exit run()
        
    else:
        bridge = kodiHue.initialSetup(monitor)    
        if not bridge:
            logger.debug("Kodi Hue: Connection failed, exiting script")
            kodiutils.notification("Kodi Hue", "Bridge not found, check your network", time=5000, icon=NOTIFICATION_ERROR, sound=True)
            return #exit run()
    
    
    #### Bridge is ready, lets GO
       
    groups=bridge.groups
    lights=bridge.lights
    testgroup=bridge.groups["9"]
    
    
    logger.debug("Kodi Hue: Initial test flash")
    
    #bridge.groups['9'].action(alert="select")
    
    testgroup.action(alert="select")
    
    #bridge.lights[5].state(bri=128, xy=[0.180,0.239],on=True, alert="select")
    #bridge.lights[5].state(bri=128,hue=0,on=True) #, alert="select")
    
    
    player = kodiHue.KodiPlayer()
    kgroup=KodiGroup.KodiGroup(bridge,player,0)

    
    if player is None:
        logger.debug('Kodi Hue: In run(), could not instantiate player')
        return
        
    
    ##Ready to go! Start running until Kodi exit.
    while connected and not monitor.abortRequested():
        ####Wait for abort
        #testgroup.action(alert="select")
        logger.debug('Kodi Hue: In process')
        xbmc.sleep(1000)
        
      
    
    return
    
##########################################################################################################################################    





