# -*- coding: utf-8 -*-

import sys
import logging
from threading import Event

import xbmc
import xbmcaddon
from xbmcgui import NOTIFICATION_ERROR,NOTIFICATION_WARNING, NOTIFICATION_INFO


#from resources.lib.qhue import Bridge
from resources.lib import kodiutils
from resources.lib.KodiGroup import KodiGroup
from resources.lib import kodiHue                                                                                                                                                          
from resources.lib import qhue


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
    logger.debug("Kodi Hue:  service started, version: {}".format(ADDON.getAddonInfo('version')))
    monitor=xbmc.Monitor()
    
    global connected
    connected = False
    
    bridgeIP = ""
    bridgeUser = ""

    if len(sys.argv) == 2:
        args = sys.argv[1]
    else: 
        args= ""
    
    logger.debug("Kodi Hue: Args: {}".format(args))



#===============================================================================
# 
#     
#     ev = Event()
#     capture = xbmc.RenderCapture()
#     fmt = capture.getImageFormat()
#     # BGRA or RGBA
#     fmtRGBA = fmt == 'RGBA'
#===============================================================================

    
###########################################################
########################################################### 
########################################################### 
###########################################################     

     
    
    if args == "discover":
        logger.debug("Kodi Hue: Started with Discovery")
        bridge = kodiHue.initialConnect(monitor, True)

    elif args.startswith("groupSelect"):
        
        kgroup=args.split("=",1)[1]
        logger.debug("Kodi Hue: Started with groupSelect. args: {}, kgroup: {}".format(args,kgroup))
        
        bridge=kodiHue.initialConnect(monitor,False,True) #don't rediscover, proceed silently
        if bridge:
            kodiHue.configureGroup(bridge,kgroup)
        else:
            logger.debug("Kodi Hue: No bridge found. Select group cancelled.")
            
            
            
    else:
        #no arguments, proceed as normal.
        logger.debug("Kodi Hue: Started with no arguments")
        bridge = kodiHue.initialConnect(monitor)
    
    
    
    if bridge:
        #got a bridge, do main script
        connected=True
        
        groups=bridge.groups
        lights=bridge.lights
        testgroup=bridge.groups["4"]
        
        
        logger.debug("Kodi Hue: Initial test flash")
        
        #bridge.groups['9'].action(alert="select")
        
        testgroup.action(alert="select")

        
        
        player = xbmc.Player 
        kgroup0=KodiGroup()
        kgroup0.setup(bridge,0,4) #kodigroup 0, huetestgroup =9
    
        

        ##Ready to go! Start running until Kodi exit.
        while connected and not monitor.abortRequested():
            logger.debug('Kodi Hue: Script waiting...')
            #TODO: restart script on Monitor.onSettingsChanged 
            ####Wait for abort
            xbmc.sleep(500)
        
        logger.debug('Kodi Hue: Process exiting...')
        return
        #### End of script
        
    else:
        logger.debug('Kodi Hue: No bridge, exiting...')
        return
        
    
