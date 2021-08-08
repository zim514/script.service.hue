import sys

import xbmc
import xbmcgui
from requests.exceptions import ConnectionError, ReadTimeout, ConnectTimeout

from resources.lib import ambigroup, kodigroup
from resources.lib import kodihue
from resources.lib import kodisettings
from resources.lib import reporting
from resources.lib.kodisettings import settings_storage
from resources.lib.language import get_string as _
from . import ADDON, cache, SETTINGS_CHANGED


def core():
    kodisettings.read_settings()

    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = ""

    monitor = kodihue.HueMonitor()

    if command:
        commands(monitor, command)
    else:
        service(monitor)


def commands(monitor, command):
    if command == "discover":
        xbmc.log("[script.service.hue] Started with Discovery")
        bridge_discovered = kodihue.discover_bridge(monitor)
        if bridge_discovered:
            bridge = kodihue.connect_bridge(monitor, silent=True)
            if bridge:
                xbmc.log("[script.service.hue] Found bridge. Running model check & starting service.")
                kodihue.check_bridge_model(bridge)
                ADDON.openSettings()
                service(monitor)

    elif command == "createHueScene":
        xbmc.log("[script.service.hue] Started with {}".format(command))
        bridge = kodihue.connect_bridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.create_hue_scene(bridge)
        else:
            xbmc.log("[script.service.hue] No bridge found. createHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        xbmc.log("[script.service.hue] Started with {}".format(command))

        bridge = kodihue.connect_bridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.delete_hue_scene(bridge)
        else:
            xbmc.log("[script.service.hue] No bridge found. deleteHueScene cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=kgroup,action  / sceneSelect=0,play
        kgroup = sys.argv[2]
        action = sys.argv[3]
        xbmc.log("[script.service.hue] Started with {}, kgroup: {}, kaction: {}".format(command, kgroup, action))

        bridge = kodihue.connect_bridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.configure_scene(bridge, kgroup, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=kgroupID
        kgroup = sys.argv[2]
        xbmc.log("[script.service.hue] Started with {}, kgroupID: {}".format(command, kgroup))

        bridge = kodihue.connect_bridge(monitor, silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.configure_ambilights(bridge, kgroup)
        else:
            xbmc.log("[script.service.hue] No bridge found. scene ambi lights cancelled.")
            xbmcgui.Dialog().notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        xbmc.log("[script.service.hue] Unknown command")
        return


def service(monitor):
    bridge = kodihue.connect_bridge(monitor, silent=settings_storage['disable_connection_message'])
    service_enabled = cache.get("script.service.hue.service_enabled")

    if bridge is not None:
        kgroups = [kodigroup.KodiGroup(0, bridge, kodigroup.VIDEO, settings_storage['initialFlash']), kodigroup.KodiGroup(1, bridge, kodigroup.AUDIO, settings_storage['initialFlash'])]
        if settings_storage['ambiEnabled']:
            ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, settings_storage['initialFlash'])

        connection_retries = 0
        timer = 60
        daylight = kodihue.get_daylight(bridge)
        cache.set("script.service.hue.daylight", daylight)
        cache.set("script.service.hue.service_enabled", True)
        xbmc.log("[script.service.hue] Core service starting")

        while settings_storage['connected'] and not monitor.abortRequested():

            # check if service was just renabled and if so restart groups
            prev_service_enabled = service_enabled
            service_enabled = cache.get("script.service.hue.service_enabled")
            if service_enabled and not prev_service_enabled:
                try:
                    kodihue.activate(bridge, kgroups, ambi_group)
                except UnboundLocalError:
                    ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, settings_storage['reloadFlash'])
                    kodihue.activate(bridge, kgroups, ambi_group)

            # process cached waiting commands
            action = cache.get("script.service.hue.action")
            if action:
                process_actions(action, kgroups)

            # reload if settings changed
            if SETTINGS_CHANGED.is_set():
                kgroups = [kodigroup.KodiGroup(0, bridge, kodigroup.VIDEO, settings_storage['reloadFlash']), kodigroup.KodiGroup(1, bridge, kodigroup.AUDIO, settings_storage['reloadFlash'])]
                if settings_storage['ambiEnabled']:
                    ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, settings_storage['reloadFlash'])
                SETTINGS_CHANGED.clear()

            # check for sunset & connection every minute
            if timer > 59:
                timer = 0
                # check connection to Hue bridge
                try:
                    if connection_retries > 0:
                        bridge = kodihue.connect_bridge(monitor, silent=True)
                        if bridge is not None:
                            new_daylight = kodihue.get_daylight(bridge)
                            connection_retries = 0
                    else:
                        new_daylight = kodihue.get_daylight(bridge)

                except (ConnectionError, ReadTimeout, ConnectTimeout) as error:
                    connection_retries = connection_retries + 1
                    if connection_retries <= 10:
                        xbmc.log("[script.service.hue] Bridge Connection Error. Attempt: {}/10 : {}".format(connection_retries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
                        timer = -60

                    else:
                        xbmc.log("[script.service.hue] Bridge Connection Error. Attempt: {}/5. Shutting down : {}".format(connection_retries, error))
                        xbmcgui.Dialog().notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
                        settings_storage['connected'] = False

                except Exception as exc:
                    xbmc.log("[script.service.hue] Get daylight exception")
                    reporting.process_exception(exc)

                # check if sunset took place
                if new_daylight != daylight:
                    xbmc.log("[script.service.hue] Daylight change. current: {}, new: {}".format(daylight, new_daylight))
                    daylight = new_daylight
                    cache.set("script.service.hue.daylight", daylight)
                    if not daylight and service_enabled:
                        xbmc.log("[script.service.hue] Sunset activate")
                        try:
                            kodihue.activate(bridge, kgroups, ambi_group)
                        except UnboundLocalError as exc:
                            kodihue.activate(bridge, kgroups)
                        except Exception as exc:
                            xbmc.log("[script.service.hue] Get daylight exception")
                            reporting.process_exception(exc)
            timer += 1
            monitor.waitForAbort(1)
        xbmc.log("[script.service.hue] Process exiting...")
        return
    xbmc.log("[script.service.hue] No connected bridge, exiting...")
    return


def process_actions(action, kgroups):
    # process an action command stored in the cache.
    action_action = action[0]
    action_kgroupid = int(action[1]) - 1
    xbmc.log("[script.service.hue] Action command: {}, action_action: {}, action_kgroupid: {}".format(action, action_action, action_kgroupid))
    if action_action == "play":
        kgroups[action_kgroupid].run_play()
    if action_action == "pause":
        kgroups[action_kgroupid].run_pause()
    if action_action == "stop":
        kgroups[action_kgroupid].run_stop()
    cache.set("script.service.hue.action", None)
