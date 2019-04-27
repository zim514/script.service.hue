# -*- coding: utf-8 -*-

import logging
import sys
from threading import Event

import xbmc
import xbmcaddon
from xbmcgui import NOTIFICATION_ERROR, NOTIFICATION_WARNING, NOTIFICATION_INFO

from KodiGroup import KodiGroup
import globals
import kodiHue
import kodiutils
import qhue
from resources.lib.globals import NUM_GROUPS


# from resources.lib.qhue import Bridge
ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))

connected = False
settingsChanged = False



#===============================================================================
# ev = Event()
# capture = xbmc.RenderCapture()
# fmt = capture.getImageFormat()
# # BGRA or RGBA
# fmtRGBA = fmt == 'RGBA'
#===============================================================================

##################################################
# # RUN
###################
def run():
    logger.debug("Kodi Hue:  service started, version: {}".format(ADDON.getAddonInfo('version')))
    
    monitor = kodiHue.HueMonitor()

    initialFlash = kodiutils.get_setting_as_bool("initialFlash")
    
    
    
    bridgeIP = ""
    bridgeUser = ""

    if len(sys.argv) == 2:
        args = sys.argv[1]
    else: 
        args = ""
    
    logger.debug("Kodi Hue: Args: {}".format(args))
    
###########################################################
########################################################### 
########################################################### 
###########################################################     




    if args.startswith("groupSelect"):
        
        kgroup = args.split("=", 1)[1]
        logger.debug("Kodi Hue: Started with groupSelect. args: {}, kgroup: {}".format(args, kgroup))
        
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.configureGroup(bridge, kgroup)
        else:
            logger.debug("Kodi Hue: No bridge found. Select group cancelled.")
            
    else:
        if args == "discover":
            logger.debug("Kodi Hue: Started with Discovery")
            bridge = kodiHue.bridgeDiscover(monitor)
            
        else:
            logger.debug("Kodi Hue: Main service started...")
            bridge = kodiHue.connectBridge(monitor,silent=False)
                    
            if bridge:
                globals.settingsChanged = False
                daylight = kodiHue.getDaylight(bridge)
                kgroups = kodiHue.setupGroups(bridge,initialFlash)
    
                timer = 0
                # #Ready to go! Start running until Kodi exit.            
                while globals.connected and not monitor.abortRequested():
                    
                    if globals.settingsChanged:
                        reloadFlash = kodiutils.get_setting_as_bool("reloadFlash")
                        kgroups = kodiHue.setupGroups(bridge, reloadFlash)
                        globals.settingsChanged = False
                    
                    timer = timer + 1
                    if timer > 60:
                        daylight = kodiHue.getDaylight(bridge)
                        
                        logger.debug('Kodi Hue: Service running...')
                        timer = 0
                        

                    
                    monitor.waitForAbort(1)
                logger.debug('Kodi Hue: Process exiting...')
                return
                
            else:
                logger.debug('Kodi Hue: No connected bridge, exiting...')
                return
