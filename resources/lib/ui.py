import xbmcgui

import bridge
from tools import notify, xbmclog


def multiselect_lights(bridge_ip, bridge_user, label, exclude,
                       preselect):
    xbmclog('Kodi Hue: In multiselect_lights(bridge_ip={}, bridge_user={}, '
            'label={}, exclude={}, preselect={})'.format(
                bridge_ip, bridge_user, label, exclude, preselect)
            )
    lights = bridge.get_lights_by_ids(bridge_ip, bridge_user)
    actual_lights = []
    items = []
    preselect_items = []
    index = 0
    for light_id, light in lights.items():
        if str(light_id) not in exclude.split(','):
            items.append(xbmcgui.ListItem(label=light.name))
            actual_lights.append(light)
            if str(light_id) in preselect.split(','):
                preselect_items.append(index)
            index += 1

    selected = xbmcgui.Dialog().multiselect(label, items,
                                            preselect=preselect_items)

    if selected:
        light_ids = [str(actual_lights[idx].light_id) for idx in selected]
        return ','.join(light_ids)
    return ''


def discover_hue_bridge(hue):
    notify("Hue Bridge Discovery", "starting")
    hue_ip = bridge.discover()
    if hue_ip is not None:
        notify("Hue Bridge Discovery", "Found bridge at: %s" % hue_ip)
        username = bridge.create_user(hue_ip)
        hue.settings.update(bridge_ip=hue_ip)
        hue.settings.update(bridge_user=username)
        hue.settings.update(connected="true")
        hue.connected = True
        notify("Hue Bridge Discovery", "Finished")
    else:
        notify("Hue Bridge Discovery", "Failed. Could not find bridge.")
