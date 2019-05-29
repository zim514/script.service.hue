# -*- coding: utf-8 -*-

import logging
import sys



import xbmcaddon
#from xbmcgui import NOTIFICATION_ERROR, NOTIFICATION_WARNING, NOTIFICATION_INFO
import xbmcgui


#from .qhue import QhueException
from .language import get_string as _


from . import globals
from . import KodiGroup
from . import kodiHue
from . import kodiutils


ADDON = xbmcaddon.Addon()
logger = logging.getLogger(__name__)
connected = False
settingsChanged = False


#===============================================================================
# ev = Event()
# capture = xbmc.RenderCapture()
# fmt = capture.getImageFormat()
# # BGRA or RGBA
# fmtRGBA = fmt == 'RGBA'
#===============================================================================


def menu():
    logger.debug("menu started, version: {}".format(ADDON.getAddonInfo('version')))
    monitor = kodiHue.HueMonitor()

    if len(sys.argv) >1:
        args = sys.argv[1]
    else: 
        args = ""

    logger.debug("Argv {}".format(sys.argv))
    logger.debug("Args: {}".format(args))

    if args == "discover":
        logger.debug("Started with Discovery")
        bridge = kodiHue.bridgeDiscover(monitor)
        if bridge:
            logger.debug("Found bridge, starting service.")
            service() #restart service
    
    elif args == "createHueGroup":
        logger.debug("Started with createGroup")
        bridge = kodiHue.connectBridge(monitor, silent=True)
        if bridge:
            kodiHue.createHueGroup(bridge)
        else: 
            logger.debug("Menu() createGroup: No bridge")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args == "deleteHueGroup":
        logger.debug("Started with deleteGroup.")
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.deleteHueGroup(bridge)
        else:
            logger.debug("No bridge found. deleteGroup cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args.startswith("groupSelect"):
        kgroup = args.split("=", 1)[1]
        logger.debug("Started with groupSelect. args: {}, kgroup: {}".format(args, kgroup))
        
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.configureGroup(bridge, kgroup)
        else:
            logger.debug("No bridge found. Select group cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    
    elif args == "createHueScene":
        logger.debug("Started with {}".format(args))
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.createHueScene(bridge)
        else:
            logger.debug("No bridge found. createHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
        
    elif args == "deleteHueScene":
        logger.debug("Started with {}".format(args))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.deleteHueScene(bridge)
        else:
            logger.debug("No bridge found. deleteHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    
    elif args == "sceneSelect": # sceneSelect=kgroup,action  / sceneSelect=0,play
            kgroup = sys.argv[2] 
            action = sys.argv[3]
            logger.debug("Started with {}, kgroup: {}, kaction: {}".format(args, kgroup, action))
            
            bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
            if bridge:
                kodiHue.configureScene(bridge, kgroup, action)
                
                #TODO: save selection
            else:
                logger.debug("No bridge found. sceneSelect cancelled.")
                xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))    
    
    else:
        #bridge = kodiHue.connectBridge(monitor, silent=True)
        #sceneUI=CreateSceneUI(bridge)
        #del sceneUI
        #No command
        ADDON.openSettings()
        
        return
         

def service():
    logger.debug(" service started, version: {}".format(ADDON.getAddonInfo('version')))
    monitor = kodiHue.HueMonitor()
    
    initialFlash = kodiutils.get_setting_as_bool("initialFlash")
    globals.forceOnSunset = kodiutils.get_setting_as_bool("forceOnSunset")
    globals.daylightDisable = kodiutils.get_setting_as_bool("daylightDisable")

    bridge = kodiHue.connectBridge(monitor,silent=False)
            
    if bridge:
        globals.settingsChanged = False
        globals.daylight = kodiHue.getDaylight(bridge)
        kgroups = kodiHue.setupGroups(bridge,initialFlash)

        timer = 60
        # #Ready to go! Start running until Kodi exit.            
        while globals.connected and not monitor.abortRequested():
            
            if globals.settingsChanged:
                reloadFlash = kodiutils.get_setting_as_bool("reloadFlash")
                forceOnSunset = kodiutils.get_setting_as_bool("forceOnSunset")
                globals.daylightDisable = kodiutils.get_setting_as_bool("daylightDisable")
                kgroups = kodiHue.setupGroups(bridge, reloadFlash)
                globals.settingsChanged = False
            
            timer = timer + 1
            if timer > 59:
                try:
                    previousDaylight = kodiHue.getDaylight(bridge)
                    logger.debug('Daylight check: current: {}, previous: {}'.format(globals.daylight, previousDaylight))
                except Exception as error:
                    logger.debug('Get daylight exception: {}'.format(error))
                    


                if globals.daylight != previousDaylight :
                    logger.debug('Daylight change! current: {}, previous: {}'.format(globals.daylight, previousDaylight))
                    globals.daylight = kodiHue.getDaylight(bridge)
                    if not globals.daylight:
                        kodiHue.sunset(bridge,kgroups)
                
                logger.debug('Service running...')
                timer = 1

            
            monitor.waitForAbort(1)
        logger.debug('Process exiting...')
        return
        
    else:
        logger.debug('No connected bridge, exiting...')
        return
    
            
         
