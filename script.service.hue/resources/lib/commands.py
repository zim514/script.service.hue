# -*- coding: utf-8 -*-

import sys

import xbmcgui

from resources.lib.core import service
from . import kodiHue, ADDON, logger
from .language import get_string as _
from . import AmbiGroup
from .kodisettings import settings


def commands():
    monitor = kodiHue.HueMonitor()

    if len(sys.argv) > 1:
        args = sys.argv[1]
    else:
        args = ""

    logger.info("menu started, version: {}, Arguments: {}".format(ADDON.getAddonInfo("version"), sys.argv))

    if args == "discover":
        logger.debug("Started with Discovery")
        bridgeDiscovered = kodiHue.bridgeDiscover(monitor)
        if bridgeDiscovered:
            bridge = kodiHue.connectBridge(monitor, silent=True)
            if bridge:
                logger.debug("Found bridge. Running model check & starting service.")
                kodiHue.checkBridgeModel(bridge)
                ADDON.openSettings()
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

    elif args == "sceneSelect":  # sceneSelect=kgroup,action  / sceneSelect=0,play
        kgroup = sys.argv[2]
        action = sys.argv[3]
        logger.debug("Started with {}, kgroup: {}, kaction: {}".format(args, kgroup, action))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.configureScene(bridge, kgroup, action)
        else:
            logger.debug("No bridge found. sceneSelect cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif args == "ambiLightSelect":  # ambiLightSelect=kgroupID
        kgroup = sys.argv[2]
        logger.debug("Started with {}, kgroupID: {}".format(args, kgroup))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.configureAmbiLights(bridge, kgroup)
        else:
            logger.debug("No bridge found. scene ambi lights cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        ADDON.openSettings()
        return
