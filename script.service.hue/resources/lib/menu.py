import sys

import xbmc
import xbmcplugin
from xbmcgui import ListItem

from resources.lib import logger, ADDON
from language import get_string as _


def menu():
    # monitor = kodiHue.HueMonitor()
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    route = sys.argv[0]

    logger.debug("Menu root started. Handle: {}, route: {}, Arguments: {}".format(addon_handle, route, sys.argv))

    if route == "plugin://script.service.hue/":

        # xbmcplugin.addDirectoryItem(addon_handle, "plugin://script.service.hue/settings", item)
        item = ListItem(_("Settings"))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url + "settings", listitem=item, isFolder=False)

        item = ListItem(_("Force Play Action"))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url + "disable", listitem=item, isFolder=False)

        item = ListItem(_("Force Pause Action"))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url + "disable", listitem=item, isFolder=False)

        item = ListItem(_("Force Stop Action"))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url + "disable", listitem=item, isFolder=False)


        item = ListItem(_("Enable"))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url + "enable", listitem=item, isFolder=False)

        item = ListItem(_("Disable"))
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url + "disable", listitem=item, isFolder=False)

        xbmcplugin.endOfDirectory(handle=addon_handle, cacheToDisc=True)

    elif route == "plugin://script.service.hue/settings":
        logger.debug("Opening settings")
        ADDON.openSettings()

    elif route == "plugin://script.service.hue/enable":
        logger.debug("Enable")
        #xbmc.executebuiltin('Skin.SetString(abc,def)')

    elif route == "plugin://script.service.hue/disable":
        logger.debug("Disable")

    elif route == "plugin://script.service.hue/force_play":
        logger.debug("Force Play")
        #xbmc.executebuiltin('Skin.SetString(abc,def)')

    elif route == "plugin://script.service.hue/force_pause":
        logger.debug("Force Pause")
        #xbmc.executebuiltin('Skin.SetString(abc,def)')


    elif route == "plugin://script.service.hue/force_stop":
                logger.debug("Force Stop")
        #xbmc.executebuiltin('Skin.SetString(abc,def)')
