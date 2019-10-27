import os
import sys
from datetime import timedelta

import xbmc
import xbmcgui
import xbmcplugin
from xbmcgui import ListItem
import simplecache

from .kodisettings import settings
from resources.lib import logger, ADDON, ADDONID, kodiHue, core, ADDONPATH
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
    cache = simplecache.SimpleCache()

    logger.debug(
        "Menu started.  route: {}, handle: {}, command: {}, parsed: {}, Arguments: {}".format(route, addon_handle,
                                                                                              command, parsed,
                                                                                              sys.argv))

    if route == "plugin://script.service.hue/":
        if not command:

            build_menu(base_url, addon_handle, cache)

        elif command == "settings":
            logger.debug("Opening settings")
            ADDON.openSettings()

        elif command == "toggle":
            if cache.get("script.service.hue.service_enabled"):
                logger.info("Disable service")
                cache.set("script.service.hue.service_enabled", False)

            else:
                logger.info("Enable service")
                cache.set("script.service.hue.service_enabled", True)
            xbmc.executebuiltin('Container.Refresh')

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
            xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=True)
            logger.debug("BUILT MENU")
        else:
            cache.set("script.service.hue.action", (action, kgroupid), expiration=(timedelta(seconds=5)))

    else:
        logger.error("Unknown command. Handle: {}, route: {}, Arguments: {}".format(addon_handle, route, sys.argv))


def build_menu(base_url, addon_handle, cache):
    items = [
        # TODO: Only display enabled groups
        (base_url + "/actions?kgroupid=1&action=menu", ListItem(_("Video Actions"), iconImage="DefaultVideo.png"), True),
        (base_url + "/actions?kgroupid=2&action=menu", ListItem(_("Audio Actions"), iconImage="DefaultAudio.png"), True),
        (base_url + "?toggle",
         ListItem(_("Hue Status: ") + (_("Enabled") if cache.get("script.service.hue.service_enabled") else _("Disabled")))),
        (base_url + "?settings", ListItem(_("Settings"), iconImage=get_icon_path("settings")))
    ]

    xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)

def get_icon_path(icon_name):
    return os.path.join(ADDONPATH, 'resources', 'icons', icon_name+".png")