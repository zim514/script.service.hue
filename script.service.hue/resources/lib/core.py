# -*- coding: utf-8 -*-

import sys
from logging import getLogger
from requests.exceptions import ConnectionError

import xbmcgui
import simplecache

from . import globals, logger, ADDON, cache, settings

from . import kodiHue
from .language import get_string as _
from . import AmbiGroup
import kodisettings


def core():
    logger.info("service started, version: {}".format(ADDON.getAddonInfo("version")))
    logger.info("Args: {}".format(sys.argv))
    kodisettings.read_settings()

    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = ""

    monitor = kodiHue.HueMonitor()
    if command:
        commands(monitor, command)
    else:
        service(monitor)


def commands(monitor, command):
    if command == "discover":
        logger.debug("Started with Discovery")
        bridge_discovered = kodiHue.bridgeDiscover(monitor)
        if bridge_discovered:
            bridge = kodiHue.connectBridge(monitor, silent=True)
            if bridge:
                logger.debug("Found bridge. Running model check & starting service.")
                kodiHue.checkBridgeModel(bridge)
                ADDON.openSettings()
                service()

    elif command == "createHueScene":
        logger.debug("Started with {}".format(command))
        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.createHueScene(bridge)
        else:
            logger.debug("No bridge found. createHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        logger.debug("Started with {}".format(command))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.deleteHueScene(bridge)
        else:
            logger.debug("No bridge found. deleteHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=kgroup,action  / sceneSelect=0,play
        kgroup = sys.argv[2]
        action = sys.argv[3]
        logger.debug("Started with {}, kgroup: {}, kaction: {}".format(command, kgroup, action))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.configureScene(bridge, kgroup, action)
        else:
            logger.debug("No bridge found. sceneSelect cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=kgroupID
        kgroup = sys.argv[2]
        logger.debug("Started with {}, kgroupID: {}".format(command, kgroup))

        bridge = kodiHue.connectBridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodiHue.configureAmbiLights(bridge, kgroup)
        else:
            logger.debug("No bridge found. scene ambi lights cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        logger.critical("Unknown command")
        return


def service(monitor):
    kodiHue.loadSettings()
    bridge = kodiHue.connectBridge(monitor, silent=settings['disable_connection_message'])
    service_enabled = cache.get("script.service.hue.service_enabled")

    if bridge is not None:
        globals.settingsChanged = False
        globals.daylight = kodiHue.getDaylight(bridge)

        kgroups = kodiHue.setupGroups(bridge, globals.initialFlash)
        if globals.ambiEnabled:
            ambi_group = AmbiGroup.AmbiGroup()
            ambi_group.setup(monitor, bridge, kgroupID=3, flash=globals.initialFlash)

        connection_retries = 0
        timer = 60  # Run loop once on first run

        cache.set("script.service.hue.service_enabled", True)
        logger.debug("Main service loop starting")

        while globals.connected and not monitor.abortRequested():

            # check if service was just renabled and if so restart groups
            prev_service_enabled = service_enabled
            service_enabled = cache.get("script.service.hue.service_enabled")
            if service_enabled and not prev_service_enabled:
                kodiHue.activate(bridge, kgroups, ambi_group)

            #process cached waiting commands
            action = cache.get("script.service.hue.action")
            if action:
                process_actions(action, kgroups)

            #reload if settings changed
            if globals.settingsChanged:
                kgroups = kodiHue.setupGroups(bridge, globals.reloadFlash)
                if globals.ambiEnabled:
                    ambi_group.setup(monitor, bridge, kgroupID=3, flash=globals.reloadFlash)
                globals.settingsChanged = False

            #check for sunset & connection every minute
            if timer > 59:
                timer = 0
                try:
                    if connection_retries > 0:
                        bridge = kodiHue.connectBridge(monitor, silent=True)
                        if bridge is not None:
                            previousDaylight = kodiHue.getDaylight(bridge)
                            connection_retries = 0
                    else:
                        previousDaylight = kodiHue.getDaylight(bridge)

                except ConnectionError as error:
                    connection_retries = connection_retries + 1
                    if connection_retries <= 5:
                        logger.error(
                            "Bridge Connection Error. Attempt: {}/5 : {}".format(connection_retries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"),
                                                      _("Connection lost. Trying again in 2 minutes"))
                        timer = -60

                    else:
                        logger.error(
                            "Bridge Connection Error. Attempt: {}/5. Shutting down : {}".format(connection_retries,
                                                                                                error))
                        xbmcgui.Dialog().notification(_("Hue Service"),
                                                      _("Connection lost. Check settings. Shutting down"))
                        globals.connected = False
                except Exception as ex:
                    logger.exception("Get daylight exception")

                #check if sunset took place
                if globals.daylight != previousDaylight:
                    logger.debug(
                        "Daylight change! current: {}, previous: {}".format(globals.daylight, previousDaylight))

                    globals.daylight = kodiHue.getDaylight(bridge)
                    if not globals.daylight and service_enabled:
                        kodiHue.activate(bridge, kgroups, ambi_group)
            timer += 1
            monitor.waitForAbort(1)
        logger.debug("Process exiting...")
        return
    logger.debug("No connected bridge, exiting...")
    return


def process_actions(action, kgroups):
    # process an action command stored in the cache.
    action_action = action[0]
    action_kgroupid = int(action[1]) - 1
    logger.debug("Action command: {}, action_action: {}, action_kgroupid: {}".format(action, action_action,
                                                                                     action_kgroupid))
    if action_action == "play":
        kgroups[action_kgroupid].run_play()
    if action_action == "pause":
        kgroups[action_kgroupid].run_pause()
    if action_action == "stop":
        kgroups[action_kgroupid].run_stop()
    cache.set("script.service.hue.action", None)
