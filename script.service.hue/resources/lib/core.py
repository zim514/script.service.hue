import sys

import requests
import xbmc

from resources.lib import ambigroup, kodigroup
from resources.lib import kodihue
from resources.lib import kodisettings
from resources.lib import reporting
from resources.lib.language import get_string as _
from . import ADDON, CACHE, SETTINGS_CHANGED
from resources.lib import globals


def core():
    kodisettings.validate_settings()

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
            bridge = kodihue.connect_bridge(silent=True)
            if bridge:
                xbmc.log("[script.service.hue] Found bridge. Running model check & starting service.")
                kodihue.check_bridge_model(bridge)
                ADDON.openSettings()
                service(monitor)

    elif command == "createHueScene":
        xbmc.log("[script.service.hue] Started with {}".format(command))
        bridge = kodihue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.create_hue_scene(bridge)
        else:
            xbmc.log("[script.service.hue] No bridge found. createHueScene cancelled.")
            kodihue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        xbmc.log("[script.service.hue] Started with {}".format(command))

        bridge = kodihue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.delete_hue_scene(bridge)
        else:
            xbmc.log("[script.service.hue] No bridge found. deleteHueScene cancelled.")
            kodihue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=kgroup,action  / sceneSelect=0,play
        kgroup = sys.argv[2]
        action = sys.argv[3]
        xbmc.log("[script.service.hue] Started with {}, kgroup: {}, kaction: {}".format(command, kgroup, action))

        bridge = kodihue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.configure_scene(bridge, kgroup, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            kodihue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=kgroupID
        kgroup = sys.argv[2]
        xbmc.log("[script.service.hue] Started with {}, kgroupID: {}".format(command, kgroup))

        bridge = kodihue.connect_bridge(silent=True)  # don't rediscover, proceed silently
        if bridge is not None:
            kodihue.configure_ambilights(bridge, kgroup)
        else:
            xbmc.log("[script.service.hue] No bridge found. scene ambi lights cancelled.")
            kodihue.notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        xbmc.log("[script.service.hue] Unknown command")
        return


def service(monitor):
    bridge = kodihue.connect_bridge(silent=ADDON.getSettingBool("disableConnectionMessage"))
    service_enabled = CACHE.get("script.service.hue.service_enabled")

    if bridge is not None:
        kgroups = [kodigroup.KodiGroup(0, bridge, kodigroup.VIDEO, ADDON.getSettingBool("initialFlash")), kodigroup.KodiGroup(1, bridge, kodigroup.AUDIO, ADDON.getSettingBool("initialFlash"))]
        if ADDON.getSettingBool("group3_enabled"):
            ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, ADDON.getSettingBool("initialFlash"))

        connection_retries = 0
        timer = 60
        daylight = kodihue.get_daylight(bridge)
        #globals.DAYLIGHT = daylight
        CACHE.set("script.service.hue.daylight", daylight)
        CACHE.set("script.service.hue.service_enabled", True)
        xbmc.log("[script.service.hue] Core service starting. Connected: {}".format(globals.CONNECTED))

        while globals.CONNECTED and not monitor.abortRequested():

            # check if service was just re-enabled and if so restart groups
            prev_service_enabled = service_enabled
            service_enabled = CACHE.get("script.service.hue.service_enabled")
           # xbmc.log("[script.service.hue] Activating ... 1")
            if service_enabled and not prev_service_enabled:
                try:
                    xbmc.log("[script.service.hue] Activating ... 2")
                    kodihue.activate(kgroups, ambi_group)
                except UnboundLocalError:
                    xbmc.log("[script.service.hue] Activating ... 3")
                    ambi_group = ambigroup.AmbiGroup(3, bridge, monitor)
                    kodihue.activate(kgroups, ambi_group)

            # if service disabled, stop ambilight thread
            if not service_enabled:
                globals.AMBI_RUNNING.clear()

            # process cached waiting commands
            action = CACHE.get("script.service.hue.action")
            if action:
                process_actions(action, kgroups)

            # reload if settings changed
            if SETTINGS_CHANGED.is_set():
                kgroups = [kodigroup.KodiGroup(0, bridge, kodigroup.VIDEO, initial_state=kgroups[0].state), kodigroup.KodiGroup(1, bridge, kodigroup.AUDIO, initial_state=kgroups[1].state)]
                if ADDON.getSettingBool("group3_enabled"):
                    ambi_group = ambigroup.AmbiGroup(3, bridge, monitor, initial_state=ambi_group.state)
                SETTINGS_CHANGED.clear()

            # check for sunset & connection every minute
            if timer > 59:
                timer = 0
                # check connection to Hue bridge
                try:
                    if connection_retries > 0:
                        bridge = kodihue.connect_bridge(silent=True)
                        if bridge is not None:
                            new_daylight = kodihue.get_daylight(bridge)
                            connection_retries = 0
                    else:
                        new_daylight = kodihue.get_daylight(bridge)

                except requests.RequestException as error:
                    connection_retries = connection_retries + 1
                    if connection_retries <= 10:
                        xbmc.log("[script.service.hue] Bridge Connection Error. Attempt: {}/10 : {}".format(connection_retries, error))
                        kodihue.notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))
                        timer = -60

                    else:
                        xbmc.log("[script.service.hue] Bridge Connection Error. Attempt: {}/5. Shutting down : {}".format(connection_retries, error))
                        kodihue.notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
                        globals.CONNECTED = False

                except Exception as exc:
                    xbmc.log("[script.service.hue] Get daylight exception")
                    reporting.process_exception(exc)

                # check if sunset took place
                if new_daylight != daylight:
                    xbmc.log("[script.service.hue] Daylight change. current: {}, new: {}".format(daylight, new_daylight))
                    daylight = new_daylight
                    #globals.DAYLIGHT = daylight
                    CACHE.set("script.service.hue.daylight", daylight)
                    if not daylight and service_enabled:
                        xbmc.log("[script.service.hue] Sunset activate")
                        try:
                            kodihue.activate(kgroups, ambi_group)
                        except UnboundLocalError as exc:
                            kodihue.activate(kgroups)
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
    CACHE.set("script.service.hue.action", None)
