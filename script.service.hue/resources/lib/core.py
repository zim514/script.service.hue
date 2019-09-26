# -*- coding: utf-8 -*-

import sys
from logging import getLogger
from requests.exceptions import ConnectionError

import xbmcgui

from . import globals
from . import kodiHue
from .language import get_string as _
from . import AmbiGroup

logger = getLogger(globals.ADDONID)

def menu():
    monitor = kodiHue.HueMonitor()

    if len(sys.argv) >1:
        args = sys.argv[1]
    else: 
        args = ""

    logger.info("menu started, version: {}, Arguments: {}".format(globals.ADDON.getAddonInfo("version"), args))

    if args == "discover":
        logger.debug("Started with Discovery")
        bridgeDiscovered = kodiHue.bridgeDiscover(monitor)
        if bridgeDiscovered:
            bridge = kodiHue.connectBridge(monitor, silent=True)
            if bridge:
                logger.debug("Found bridge. Running model check & starting service.")
                kodiHue.checkBridgeModel(bridge)
                globals.ADDON.openSettings()
                service()

    elif args == "createHueScene":
        logger.debug("Started with {}".format(args))
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.createHueScene(bridge)
        else:
            logger.debug("No bridge found. createHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args == "deleteHueScene":
        logger.debug("Started with {}".format(args))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.deleteHueScene(bridge)
        else:
            logger.debug("No bridge found. deleteHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args == "sceneSelect": # sceneSelect=kgroup,action  / sceneSelect=0,play
            kgroup = sys.argv[2]
            action = sys.argv[3]
            logger.debug("Started with {}, kgroup: {}, kaction: {}".format(args, kgroup, action))

            bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
            if bridge is not None:
                kodiHue.configureScene(bridge, kgroup, action)
            else:
                logger.debug("No bridge found. sceneSelect cancelled.")
                xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))    

    elif args == "ambiLightSelect": # ambiLightSelect=kgroupID 
            kgroup = sys.argv[2]
            logger.debug("Started with {}, kgroupID: {}".format(args, kgroup))

            bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
            if bridge is not None:
                kodiHue.configureAmbiLights(bridge, kgroup)
            else:
                logger.debug("No bridge found. scene ambi lights cancelled.")
                xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))    
    else:
        globals.ADDON.openSettings()
        return


def service():
    logger.info("service started, version: {}".format(globals.ADDON.getAddonInfo("version")))
    kodiHue.loadSettings()
    monitor = kodiHue.HueMonitor()


    bridge = kodiHue.connectBridge(monitor,silent=False)

    if bridge is not None:
        globals.settingsChanged = False
        globals.daylight = kodiHue.getDaylight(bridge)
       
        kgroups = kodiHue.setupGroups(bridge,globals.initialFlash)
        if globals.ambiEnabled:
            ambiGroup = AmbiGroup.AmbiGroup()
            ambiGroup.setup(monitor,bridge, kgroupID=3, flash=globals.initialFlash)
        
        connectionRetries = 0
        timer = 60 #Run loop once on first run
        # #Ready to go! Start running until Kodi exit.
        logger.debug("Main service loop starting")
        while globals.connected and not monitor.abortRequested():
            
               
            if globals.settingsChanged:
                kgroups = kodiHue.setupGroups(bridge, globals.reloadFlash)
                if globals.ambiEnabled:
                    ambiGroup.setup(monitor,bridge, kgroupID=3, flash=globals.reloadFlash)
                globals.settingsChanged = False


            if timer > 59: 
                timer = 0
                try:
                    if connectionRetries > 0:
                        bridge = kodiHue.connectBridge(monitor,silent=True)
                        if bridge is not None:
                            previousDaylight = kodiHue.getDaylight(bridge)
                            connectionRetries = 0
                    else:
                        previousDaylight = kodiHue.getDaylight(bridge)
                        
                except ConnectionError as error:
                    connectionRetries = connectionRetries + 1
                    if connectionRetries <= 5:
                        logger.error("Bridge Connection Error. Attempt: {}/5 : {}".format(connectionRetries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
                        timer = -60 
                        
                    else:
                        logger.error("Bridge Connection Error. Attempt: {}/5. Shutting down : {}".format(connectionRetries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
                        globals.connected = False
                except Exception as ex:
                    logger.exception("Get daylight exception")


                if globals.daylight != previousDaylight :
                    logger.debug("Daylight change! current: {}, previous: {}".format(globals.daylight, previousDaylight))
                    
                    globals.daylight = kodiHue.getDaylight(bridge)
                    if not globals.daylight:
                        kodiHue.sunset(bridge,kgroups,ambiGroup)
                        
            timer += 1
            monitor.waitForAbort(1)
        logger.debug("Process exiting...")
        return
    logger.debug("No connected bridge, exiting...")
    return
