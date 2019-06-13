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

kodiutils.configLog()



#===============================================================================
# ev = Event()
# capture = xbmc.RenderCapture()
# fmt = capture.getImageFormat()
# # BGRA or RGBA
# fmtRGBA = fmt == 'RGBA'
#===============================================================================


def menu():
    kodiutils.log("menu started, version: {}".format(globals.ADDON.getAddonInfo('version')))
    monitor = kodiHue.HueMonitor()

    if len(sys.argv) >1:
        args = sys.argv[1]
    else: 
        args = ""

    kodiutils.log("Argv {}".format(sys.argv))
    kodiutils.log("Args: {}".format(args))

    if args == "discover":
        kodiutils.log("Started with Discovery")
        bridge = kodiHue.bridgeDiscover(monitor)
        if bridge:
            kodiutils.log("Found bridge, starting service.")
            service() #restart service
    
    elif args == "createHueGroup":
        kodiutils.log("Started with createGroup")
        bridge = kodiHue.connectBridge(monitor, silent=True)
        if bridge:
            kodiHue.createHueGroup(bridge)
        else: 
            kodiutils.log("Menu() createGroup: No bridge")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args == "deleteHueGroup":
        kodiutils.log("Started with deleteGroup.")
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.deleteHueGroup(bridge)
        else:
            kodiutils.log("No bridge found. deleteGroup cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args.startswith("groupSelect"):
        kgroup = args.split("=", 1)[1]
        kodiutils.log("Started with groupSelect. args: {}, kgroup: {}".format(args, kgroup))
        
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.configureGroup(bridge, kgroup)
        else:
            kodiutils.log("No bridge found. Select group cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    
    elif args == "createHueScene":
        kodiutils.log("Started with {}".format(args))
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.createHueScene(bridge)
        else:
            kodiutils.log("No bridge found. createHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
        
    elif args == "deleteHueScene":
        kodiutils.log("Started with {}".format(args))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge:
            kodiHue.deleteHueScene(bridge)
        else:
            kodiutils.log("No bridge found. deleteHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    
    elif args == "sceneSelect": # sceneSelect=kgroup,action  / sceneSelect=0,play
            kgroup = sys.argv[2]
            action = sys.argv[3]
            kodiutils.log("Started with {}, kgroup: {}, kaction: {}".format(args, kgroup, action))
            
            bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
            if bridge:
                kodiHue.configureScene(bridge, kgroup, action)
                
                #TODO: save selection
            else:
                kodiutils.log("No bridge found. sceneSelect cancelled.")
                xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))    
    
    else:
        #bridge = kodiHue.connectBridge(monitor, silent=True)
        #sceneUI=CreateSceneUI(bridge)
        #del sceneUI
        #No command
        globals.ADDON.openSettings()
        
        return
         

def service():
    kodiutils.log(" service started, version: {}".format(globals.ADDON.getAddonInfo('version')))
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
                globals.forceOnSunset = kodiutils.get_setting_as_bool("forceOnSunset")
                globals.daylightDisable = kodiutils.get_setting_as_bool("daylightDisable")
                
                kgroups = kodiHue.setupGroups(bridge, reloadFlash)
                globals.settingsChanged = False
            
            timer = timer + 1
            if timer > 59:
                try:
                    previousDaylight = kodiHue.getDaylight(bridge)
                    kodiutils.log('Daylight check: current: {}, previous: {}'.format(globals.daylight, previousDaylight))
                except Exception as error:
                    kodiutils.log('Get daylight exception: {}'.format(error))
                    


                if globals.daylight != previousDaylight :
                    kodiutils.log('Daylight change! current: {}, previous: {}'.format(globals.daylight, previousDaylight))
                    globals.daylight = kodiHue.getDaylight(bridge)
                    if not globals.daylight:
                        kodiHue.sunset(bridge,kgroups)
                
                kodiutils.log('Service running...')
                timer = 1

            
            monitor.waitForAbort(1)
        kodiutils.log('Process exiting...')
        return
        
    else:
        kodiutils.log('No connected bridge, exiting...')
        return
    