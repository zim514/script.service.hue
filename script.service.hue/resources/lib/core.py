#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.
import datetime
import json
import sys
import threading

import xbmc

from . import ADDON, SETTINGS_CHANGED, ADDONID, AMBI_RUNNING
from . import ambigroup, lightgroup, kodiutils, hueconnection
from .hueconnection import HueConnection
from .kodiutils import validate_settings, notification, cache_set, cache_get
from .language import get_string as _
from .huev2 import HueAPIv2


def core():
    kodiutils.validate_settings()
    monitor = HueMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        _commands(monitor, command)
    else:
        _service(monitor)


def _commands(monitor, command):
    xbmc.log(f"[script.service.hue] Started with {command}")

    if command == "discover":
        hue_connection = hueconnection.HueConnection(monitor, silent=True, discover=True)
        if hue_connection.connected:
            xbmc.log("[script.service.hue] Found bridge. Starting service.")
            ADDON.openSettings()
            _service(monitor)
        else:
            ADDON.openSettings()

    elif command == "createHueScene":
        hue_connection = hueconnection.HueConnection(monitor, silent=True,
                                                     discover=False)  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.create_hue_scene()
        else:
            xbmc.log("[script.service.hue] No bridge found. createHueScene cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "deleteHueScene":
        hue_connection = hueconnection.HueConnection(monitor, silent=True,
                                                     discover=False)  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.delete_hue_scene()
        else:
            xbmc.log("[script.service.hue] No bridge found. deleteHueScene cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "sceneSelect":  # sceneSelect=light_group,action  / sceneSelect=0,play
        light_group = sys.argv[2]
        action = sys.argv[3]
        # xbmc.log(f"[script.service.hue] sceneSelect: light_group: {light_group}, action: {action}")

        hue_connection = hueconnection.HueConnection(monitor, silent=True,
                                                     discover=False)  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.configure_scene(light_group, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    elif command == "ambiLightSelect":  # ambiLightSelect=light_group_id
        light_group = sys.argv[2]
        # xbmc.log(f"[script.service.hue] ambiLightSelect light_group_id: {light_group}")

        hue_connection = hueconnection.HueConnection(monitor, silent=True,
                                                     discover=False)  # don't rediscover, proceed silently  # don't rediscover, proceed silently
        if hue_connection.connected:
            hue_connection.configure_ambilights(light_group)
        else:
            xbmc.log("[script.service.hue] No bridge found. Select ambi lights cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))
    else:
        xbmc.log(f"[script.service.hue] Unknown command: {command}")
        raise RuntimeError(f"Unknown Command: {command}")


def _service(monitor):
    service_enabled = cache_get("service_enabled")

    #### V1 Connection - reliable discovery and config
    hue_connection = HueConnection(monitor, silent=ADDON.getSettingBool("disableConnectionMessage"), discover=False)

    #### V2 Connection - this has no proper bridge discovery, and missing all kinds of error checking
    bridge = HueAPIv2(monitor, ip=ADDON.getSetting("bridgeIP"), key=ADDON.getSetting("bridgeUser"))

    if bridge.connected and hue_connection.connected:
        # light groups still expect a V1 bridge object
        light_groups = [lightgroup.LightGroup(0, hue_connection, lightgroup.VIDEO), lightgroup.LightGroup(1, hue_connection, lightgroup.AUDIO), ambigroup.AmbiGroup(3, hue_connection)]

        #start sunset and midnight timers
        timers = Timers(monitor, bridge, light_groups)
        timers.start()

        cache_set("service_enabled", True)
        # xbmc.log("[script.service.hue] Core service starting. Connected: {}".format(CONNECTED))

        while hue_connection.connected and bridge.connected and not monitor.abortRequested():

            # check if service was just re-enabled and if so activate groups
            prev_service_enabled = service_enabled
            service_enabled = cache_get("service_enabled")
            if service_enabled and not prev_service_enabled:
                activate(light_groups)

            # if service was disabled, stop ambilight thread
            if not service_enabled:
                AMBI_RUNNING.clear()

            # process CACHED waiting commands
            action = cache_get("action")
            if action:
                _process_actions(action, light_groups)

            # reload groups if settings changed, but keep player state
            if SETTINGS_CHANGED.is_set():
                light_groups = [
                    lightgroup.LightGroup(0, hue_connection, lightgroup.VIDEO, initial_state=light_groups[0].state, video_info_tag=light_groups[0].video_info_tag),
                    lightgroup.LightGroup(1, hue_connection, lightgroup.AUDIO, initial_state=light_groups[1].state, video_info_tag=light_groups[1].video_info_tag),
                    ambigroup.AmbiGroup(3, hue_connection, initial_state=light_groups[2].state, video_info_tag=light_groups[2].video_info_tag)]
                SETTINGS_CHANGED.clear()

            monitor.waitForAbort(1)
        xbmc.log("[script.service.hue] Process exiting...")
        return
    xbmc.log("[script.service.hue] No connected hue_connection, exiting...")
    return


def _process_actions(action, light_groups):
    # process an action command stored in the CACHE.
    action_action = action[0]
    action_light_group_id = int(action[1]) - 1
    xbmc.log(f"[script.service.hue] Action command: {action}, action_action: {action_action}, action_light_group_id: {action_light_group_id}")
    light_groups[action_light_group_id].run_action(action_action)

    cache_set("action", None)


class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

    def onSettingsChanged(self):
        # xbmc.log("[script.service.hue] Settings changed")
        validate_settings()
        SETTINGS_CHANGED.set()

    def onNotification(self, sender, method, data):
        if sender == ADDONID:
            xbmc.log(f"[script.service.hue] Notification received: method: {method}, data: {data}")

            if method == "Other.disable":
                xbmc.log("[script.service.hue] Notification received: Disable")
                cache_set("service_enabled", False)

            if method == "Other.enable":
                xbmc.log("[script.service.hue] Notification received: Enable")
                cache_set("service_enabled", True)

            if method == "Other.actions":
                json_loads = json.loads(data)

                light_group_id = json_loads['group']
                action = json_loads['command']
                xbmc.log(f"[script.service.hue] Action Notification: group: {light_group_id}, command: {action}")
                cache_set("script.service.hue.action", (action, light_group_id))


def activate(light_groups):
    """
    Activates play action as appropriate for all groups. Used at sunset and when service is re-enabled via Actions.
    """
    xbmc.log(f"[script.service.hue] Activating scenes: light_groups: {light_groups}")

    for g in light_groups:
        xbmc.log(f"[script.service.hue] in activate g: {g}, light_group_id: {g.light_group_id}")
        if ADDON.getSettingBool(f"group{g.light_group_id}_enabled"):
            g.activate()


class Timers(threading.Thread):
    def __init__(self, monitor, bridge, light_groups):
        super().__init__()
        self.monitor = monitor
        self.bridge = bridge
        self.light_groups = light_groups

    def run(self):
        self._schedule()

    def _run_midnight(self):
        # get new day's sunset time after midnight
        self.bridge.update_sunset()
        xbmc.log(f"[script.service.hue] in run_midnight(): 1 minute past midnight, new sunset time: {self.bridge.sunset}")

    def _run_sunset(self):
        # The function you want to run at sunset
        activate(self.light_groups)
        xbmc.log(f"[script.service.hue] in run_sunset(): Sunset. ")

    @staticmethod
    def _calculate_initial_delay(target_time):
        # Calculate the delay until the target time
        now = datetime.datetime.now().time()
        target_datetime = datetime.datetime.combine(datetime.date.today(), target_time)
        if target_time < now:
            target_datetime += datetime.timedelta(days=1)
        delay = (target_datetime - datetime.datetime.now()).total_seconds()
        return delay

    def _schedule(self):
        while not self.monitor.abortRequested():
            # Calculate delay for sunset and wait
            delay_sunset = self._calculate_initial_delay(self.bridge.sunset)
            xbmc.log(f"[script.service.hue] in schedule(): Sunset will run in {delay_sunset} seconds")
            if self.monitor.waitForAbort(delay_sunset):
                # Abort was requested while waiting. We should exit
                break
            self._run_sunset()

            # Calculate delay for midnight and wait
            midnight_plus_one = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=0, minute=1, second=0, microsecond=0).time()
            delay_midnight = self._calculate_initial_delay(midnight_plus_one)
            xbmc.log(f"[script.service.hue] in schedule(): Midnight will run in {delay_midnight} seconds")
            if self.monitor.waitForAbort(delay_midnight):
                # Abort was requested while waiting. We should exit
                break
            self._run_midnight()
