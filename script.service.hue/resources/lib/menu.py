import sys

import xbmc
import xbmcgui
import xbmcplugin
from xbmcgui import ListItem
from .kodisettings import settings
from resources.lib import logger, ADDON, ADDONID, kodiHue, core
from language import get_string as _

try:
    # Python 3
    from urllib.parse import urlparse, parse_qs
except ImportError:
    # Python 2
    from urlparse import urlparse, parse_qs


def menu():
    route = sys.argv[0]
    addon_handle = int(sys.argv[1])
    base_url = sys.argv[0]
    command = sys.argv[2][1:]
    parsed = parse_qs(command)

    logger.debug(
        "Menu started.  route: {}, handle: {}, command: {}, parsed: {}, Arguments: {}".format(route, addon_handle, command, parsed, sys.argv))

    if route == "plugin://script.service.hue/":
        if not command:

            # List - list of (url, listitem[, isFolder]) as a tuple to add.
            items = [
                # TODO: Only display enabled groups
                (base_url + "/actions?kgroupid=1&action=menu", ListItem(_("Video Actions")), True),
                (base_url + "/actions?kgroupid=2&action=menu", ListItem(_("Audio Actions")), True),
                (base_url + "?enable", ListItem(_("Enable"))),
                (base_url + "?disable", ListItem(_("Disable"))),
                (base_url + "?settings", ListItem(_("Settings")))
            ]

            xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
            xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)

        elif command == "settings":
            logger.debug("Opening settings")
            ADDON.openSettings()

        elif command == "enable":
            logger.debug("Enable service")
            if not settings['service_enabled']:
                ADDON.setSettingBool("service_enabled", True)
                from .core import service
                service()

        elif command == "disable":
            logger.debug("Disable service")
            ADDON.setSettingBool("service_enabled", False)

    elif route == "plugin://script.service.hue/actions":
        action = parsed['action'][0]
        kgroupid = parsed['kgroupid'][0]
        logger.debug("Actions: {}, kgroupid: {}".format(action, kgroupid))
        if action == "menu":
            items = [

                (base_url + "?action=play&kgroupid=" + kgroupid, ListItem(_("Play"))),
                (base_url + "?action=pause&kgroupid=" + kgroupid, ListItem(_("Pause"))),
                (base_url + "?action=stop&kgroupid=" + kgroupid, ListItem(_("Stop"))),
            ]

            xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
            xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)
            logger.debug("BUILT MENU")
        elif command == "play":
            # TODO make actions work.
            pass
        elif command == "pause":
            pass
        elif command == "stop":
            pass



    else:
        logger.error("Unknown command. Handle: {}, route: {}, Arguments: {}".format(addon_handle, route, sys.argv))
