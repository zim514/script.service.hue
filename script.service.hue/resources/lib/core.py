import sys

import requests
import xbmc

from resources.lib import ADDON, CACHE, SETTINGS_CHANGED
from resources.lib import ambigroup, lightgroup, AMBI_RUNNING, CONNECTED
from resources.lib import hue, reporting, settings
from resources.lib.language import get_string as _


def core():
    settings.validate_settings()

    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = ""

    monitor = hue.HueMonitor()

    if command:
        commands(monitor, command)
    else:
        service(monitor)


def commands(monitor, command):
    if command == "discover":
        xbmc.log("[script.service.hue] Started with Discovery")
        bridge_discovered = hue.discover_bridge(monitor)
        if bridge_discovered:
            bridge = hue.connect_bridge(silent=True)
            if bridge:
                xbmc.log("[script.service.hue] Found bridge. Running model check & starting service.")
                hue.check_bridge_model(bridge)
                ADDON.openSettings()
                service(monitor)

    elif command == "createHueScene":
        xbmc.log(f"[script.service.hue] Started with {command}")
        bridge = hue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            hue.create_hue_scene(bridge)
        else:
            xbmc.log("[script.service.hue] No bridge found. createHueScene cancelled.")
            hue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        xbmc.log(f"[script.service.hue] Started with {command}")

        bridge = hue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            hue.delete_hue_scene(bridge)
        else:
            xbmc.log("[script.service.hue] No bridge found. deleteHueScene cancelled.")
            hue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=light_group,action  / sceneSelect=0,play
        light_group = sys.argv[2]
        action = sys.argv[3]
        xbmc.log(f"[script.service.hue] Started with {command}, light_group: {light_group}, action: {action}")

        bridge = hue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            hue.configure_scene(bridge, light_group, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            hue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=light_group_id
        light_group = sys.argv[2]
        xbmc.log(f"[script.service.hue] Started with {command}, light_group_id: {light_group}")

        bridge = hue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            hue.configure_ambilights(bridge, light_group)
        else:
            xbmc.log("[script.service.hue] No bridge found. scene ambi lights cancelled.")
            hue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        xbmc.log("[script.service.hue] Unknown command")
        return


def service(monitor):
    bridge = hue.connect_bridge(silent=ADDON.getSettingBool("disableConnectionMessage"))
    service_enabled = CACHE.get("script.service.hue.service_enabled")
    initial_flash = ADDON.getSettingBool("initialFlash")

    if bridge is not None:
        light_groups = [lightgroup.LightGroup(0, bridge, lightgroup.VIDEO, initial_flash), lightgroup.LightGroup(1, bridge, lightgroup.AUDIO, initial_flash)]
        if ADDON.getSettingBool("group3_enabled"):
            ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, initial_flash)

        connection_retries = 0
        timer = 60
        daylight = hue.get_daylight(bridge)
        new_daylight = daylight

        CACHE.set("script.service.hue.daylight", daylight)
        CACHE.set("script.service.hue.service_enabled", True)
        # xbmc.log("[script.service.hue] Core service starting. Connected: {}".format(CONNECTED))

        while CONNECTED.is_set() and not monitor.abortRequested():

            # check if service was just re-enabled and if so restart groups
            prev_service_enabled = service_enabled
            service_enabled = CACHE.get("script.service.hue.service_enabled")

            if service_enabled and not prev_service_enabled:
                try:
                    hue.activate(light_groups, ambi_group)
                except UnboundLocalError:
                    ambi_group = ambigroup.AmbiGroup(3, bridge, monitor)
                    hue.activate(light_groups, ambi_group)

            # if service disabled, stop ambilight._ambi_loop thread
            if not service_enabled:
                AMBI_RUNNING.clear()

            # process cached waiting commands
            action = CACHE.get("script.service.hue.action")
            if action:
                _process_actions(action, light_groups)

            # reload if settings changed
            if SETTINGS_CHANGED.is_set():
                light_groups = [lightgroup.LightGroup(0, bridge, lightgroup.VIDEO, initial_state=light_groups[0].state, video_info_tag=light_groups[0].video_info_tag),
                                lightgroup.LightGroup(1, bridge, lightgroup.AUDIO, initial_state=light_groups[1].state, video_info_tag=light_groups[1].video_info_tag)]
                if ADDON.getSettingBool("group3_enabled"):
                    try:
                        ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, initial_state=ambi_group.state, video_info_tag=ambi_group.video_info_tag)
                    except UnboundLocalError:
                        ambi_group = ambigroup.AmbiGroup(3, bridge, monitor)  # if ambi_group is constructed for the first time.
                SETTINGS_CHANGED.clear()

            # check for sunset & connection every minute
            if timer > 59:
                timer = 0
                # check connection to Hue bridge
                try:
                    if connection_retries > 0:
                        bridge = hue.connect_bridge(silent=True)
                        if bridge is not None:
                            new_daylight = hue.get_daylight(bridge)
                            connection_retries = 0
                    else:
                        new_daylight = hue.get_daylight(bridge)

                except requests.RequestException as error:
                    connection_retries = connection_retries + 1
                    if connection_retries <= 10:
                        xbmc.log(f"[script.service.hue] Bridge Connection Error. Attempt: {connection_retries}/10 : {error}")
                        hue.notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
                        timer = -60

                    else:
                        xbmc.log(f"[script.service.hue] Bridge Connection Error. Attempt: {connection_retries}/5. Shutting down : {error}")
                        hue.notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
                        CONNECTED.clear()

                except Exception as exc:
                    xbmc.log("[script.service.hue] Get daylight exception")
                    reporting.process_exception(exc)

                # check if sunset took place
                if new_daylight != daylight:
                    xbmc.log(f"[script.service.hue] Daylight change. current: {daylight}, new: {new_daylight}")
                    daylight = new_daylight

                    CACHE.set("script.service.hue.daylight", daylight)
                    if not daylight and service_enabled:
                        xbmc.log("[script.service.hue] Sunset activate")
                        try:
                            hue.activate(light_groups, ambi_group)
                        except UnboundLocalError:
                            hue.activate(light_groups)  # if no ambi_group, activate light_groups
                        except Exception as exc:
                            xbmc.log("[script.service.hue] Get daylight exception")
                            reporting.process_exception(exc)
            timer += 1
            monitor.waitForAbort(1)
        xbmc.log("[script.service.hue] Process exiting...")
        return
    xbmc.log("[script.service.hue] No connected bridge, exiting...")
    return


def _process_actions(action, light_groups):
    # process an action command stored in the cache.
    action_action = action[0]
    action_light_group_id = int(action[1]) - 1
    xbmc.log(f"[script.service.hue] Action command: {action}, action_action: {action_action}, action_light_group_id: {action_light_group_id}")
    light_groups[action_light_group_id].run_scene(action_action)
    CACHE.set("script.service.hue.action", None)
