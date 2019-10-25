# -*- coding: utf-8 -*-

import sys
from logging import getLogger
from requests.exceptions import ConnectionError

import xbmcgui

from . import globals, logger, ADDON
from . import kodiHue
from .language import get_string as _
from . import AmbiGroup
from .kodisettings import settings


def service():
    logger.info("service started, version: {}".format(ADDON.getAddonInfo("version")))
    kodiHue.loadSettings()
    monitor = kodiHue.HueMonitor()

    bridge = kodiHue.connectBridge(monitor, silent=globals.disableConnectionMessage)

    if bridge is not None:
        globals.settingsChanged = False
        globals.daylight = kodiHue.getDaylight(bridge)

        kgroups = kodiHue.setupGroups(bridge, globals.initialFlash)
        if globals.ambiEnabled:
            ambiGroup = AmbiGroup.AmbiGroup()
            ambiGroup.setup(monitor, bridge, kgroupID=3, flash=globals.initialFlash)

        connection_retries = 0
        timer = 60  # Run loop once on first run
        # #Ready to go! Start running until Kodi exit.
        logger.debug("Main service loop starting")

        while globals.connected and settings['service_enabled'] and not monitor.abortRequested():

            if globals.settingsChanged:
                kgroups = kodiHue.setupGroups(bridge, globals.reloadFlash)
                if globals.ambiEnabled:
                    ambiGroup.setup(monitor, bridge, kgroupID=3, flash=globals.reloadFlash)
                globals.settingsChanged = False

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
                        logger.error("Bridge Connection Error. Attempt: {}/5 : {}".format(connection_retries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
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

                if globals.daylight != previousDaylight:
                    logger.debug(
                        "Daylight change! current: {}, previous: {}".format(globals.daylight, previousDaylight))

                    globals.daylight = kodiHue.getDaylight(bridge)
                    if not globals.daylight:
                        kodiHue.sunset(bridge, kgroups, ambiGroup)

            timer += 1
            monitor.waitForAbort(1)
        logger.debug("Process exiting...")
        return
    logger.debug("No connected bridge, exiting...")
    return
