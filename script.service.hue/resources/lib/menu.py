import sys
from datetime import timedelta
from urllib.parse import parse_qs

import xbmc
import xbmcplugin
from xbmcgui import ListItem

from resources.lib import ADDON, CACHE
from .language import get_string as _


def menu():
    route = sys.argv[0]
    addon_handle = int(sys.argv[1])
    base_url = sys.argv[0]
    command = sys.argv[2][1:]
    parsed = parse_qs(command)

    if route == "plugin://script.service.hue/":
        if not command:
            build_menu(base_url, addon_handle)

        elif command == "settings":
            # xbmc.log("[script.service.hue] Opening settings")
            ADDON.openSettings()

        elif command == "toggle":
            if CACHE.get("script.service.hue.service_enabled") and get_status() != "Disabled by daylight":
                xbmc.log("[script.service.hue] Disable service")
                CACHE.set("script.service.hue.service_enabled", False)

            elif get_status() != "Disabled by daylight":
                xbmc.log("[script.service.hue] Enable service")
                CACHE.set("script.service.hue.service_enabled", True)
            else:
                xbmc.log("[script.service.hue] Disabled by daylight, ignoring")

            xbmc.executebuiltin('Container.Refresh')

    elif route == "plugin://script.service.hue/actions":
        action = parsed['action'][0]
        light_group_id = parsed['light_group_id'][0]
        xbmc.log(f"[script.service.hue] Actions: {action}, light_group_id: {light_group_id}")
        if action == "menu":
            items = [
                (base_url + "?action=play&light_group_id=" + light_group_id, ListItem(_("Play"))),
                (base_url + "?action=pause&light_group_id=" + light_group_id, ListItem(_("Pause"))),
                (base_url + "?action=stop&light_group_id=" + light_group_id, ListItem(_("Stop")))
            ]

            xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
            xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=True)
        else:
            CACHE.set("script.service.hue.action", (action, light_group_id), expiration=(timedelta(seconds=5)))
    else:
        xbmc.log(f"[script.service.hue] Unknown command. Handle: {addon_handle}, route: {route}, Arguments: {sys.argv}")


def build_menu(base_url, addon_handle):
    items = [
        (base_url + "/actions?light_group_id=1&action=menu", ListItem(_("Video Actions")), True),
        (base_url + "/actions?light_group_id=2&action=menu", ListItem(_("Audio Actions")), True),
        (base_url + "?toggle", ListItem(_("Hue Status: ") + get_status())),
        (base_url + "?settings", ListItem(_("Settings")))
    ]

    xbmcplugin.addDirectoryItems(addon_handle, items, len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=False)


def get_status():
    enabled = CACHE.get("script.service.hue.service_enabled")
    daylight = CACHE.get("script.service.hue.daylight")
    daylight_disable = ADDON.getSettingBool("daylightDisable")
    # xbmc.log("[script.service.hue] Current status: {}".format(daylight_disable))
    if daylight and daylight_disable:
        return _("Disabled by daylight")
    elif enabled:
        return _("Enabled")
    return _("Disabled")
