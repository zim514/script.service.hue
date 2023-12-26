#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.
from datetime import datetime
import json
import sys
import threading

import xbmc

from . import ADDON, SETTINGS_CHANGED, ADDONID, AMBI_RUNNING
from . import lightgroup, kodiutils, ambigroup
from .hue import Hue
from .kodiutils import validate_settings, notification, cache_set, cache_get, convert_time
from .language import get_string as _


def core():
    kodiutils.validate_settings()
    monitor = HueMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        command_args = sys.argv[2:]

        command_handler = CommandHandler(monitor)
        command_handler.handle_command(command, *command_args)
    else:
        service = HueService(monitor)
        service.run()


class CommandHandler:
    def __init__(self, monitor):
        self.monitor = monitor
        self.commands = {
            "discover": self.discover,
            "sceneSelect": self.scene_select,
            "ambiLightSelect": self.ambi_light_select
        }

    def handle_command(self, command, *args):
        xbmc.log(f"[script.service.hue] Started with {command}")
        command_func = self.commands.get(command)

        if command_func:
            command_func(*args)
        else:
            xbmc.log(f"[script.service.hue] Unknown command: {command}")
            raise RuntimeError(f"Unknown Command: {command}")

    def discover(self):
        bridge = Hue(self.monitor, discover=True)
        if bridge.connected:
            xbmc.log("[script.service.hue] Found bridge. Opening settings.")
            ADDON.openSettings()

        else:
            xbmc.log("[script.service.hue] No bridge found. Opening settings.")
            ADDON.openSettings()

    def scene_select(self, light_group, action):
        xbmc.log(f"[script.service.hue] sceneSelect: light_group: {light_group}, action: {action}")
        bridge = Hue(self.monitor)
        if bridge.connected:
            bridge.configure_scene(light_group, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    def ambi_light_select(self, light_group):
        bridge = Hue(self.monitor)
        if bridge.connected:
            bridge.configure_ambilights(light_group)
        else:
            xbmc.log("[script.service.hue] No bridge found. Select ambi lights cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))


class HueService:
    def __init__(self, monitor):
        self.monitor = monitor
        self.bridge = Hue(monitor)
        self.light_groups = []
        self.timers = None
        self.service_enabled = True
        cache_set("service_enabled", True)

    def run(self):

        self.light_groups = self.initialize_light_groups()
        self.timers = Timers(self.monitor, self.bridge, self)

        if self.bridge.connected:
            self.timers.start()

        # Track the previous state of the service
        prev_service_enabled = self.service_enabled

        while not self.monitor.abortRequested():
            # Update the current state of the service
            self.service_enabled = cache_get("service_enabled")

            if self.service_enabled:
                self._reload_settings_if_needed()
                self._process_actions()

                # If the service was previously disabled and is now enabled, activate light groups
                if not prev_service_enabled and self.bridge.connected:
                    self.activate()
            else:
                AMBI_RUNNING.clear()

            # If the bridge gets disconnected, stop the timers
            if not self.bridge.connected and self.timers.is_alive():
                self.timers.stop()

            # If the bridge gets reconnected, restart the timers
            if self.bridge.connected and not self.timers.is_alive():
                self.timers.start()

            # Update the previous state for the next iteration
            prev_service_enabled = self.service_enabled

            if self.monitor.waitForAbort(1):
                break

        xbmc.log("[script.service.hue] Abort requested...")

    def initialize_light_groups(self):
        # Initialize light groups
        return [
            lightgroup.LightGroup(0, lightgroup.VIDEO, self.bridge),
            lightgroup.LightGroup(1, lightgroup.AUDIO, self.bridge),
            ambigroup.AmbiGroup(3, self.monitor, self.bridge)
        ]

    def activate(self):
        # Activates play action as appropriate for all groups. Used at sunset and when service is re-enabled via Actions.
        xbmc.log(f"[script.service.hue] Activating scenes")

        for g in self.light_groups:
            if ADDON.getSettingBool(f"group{g.light_group_id}_enabled"):
                g.activate()

    def _process_actions(self):
        # Retrieve an action command stored in the CACHE.
        action = cache_get("action")

        # Check if the action is not None or not empty
        if action:
            action_action = action[0]
            action_light_group_id = int(action[1]) - 1
            xbmc.log(f"[script.service.hue] Action command: {action}, action_action: {action_action}, action_light_group_id: {action_light_group_id}")

            # Run the action
            self.light_groups[action_light_group_id].run_action(action_action)

            # Clear the action from the cache after processing
            cache_set("action", None)

    def _reload_settings_if_needed(self):
        if SETTINGS_CHANGED.is_set():
            old_ip = self.bridge.ip
            old_key = self.bridge.key
            # Reload settings

            for group in self.light_groups:
                group.reload_settings()
            self.bridge.reload_settings()

            # If IP or key has changed, attempt to reconnect
            if (old_ip != self.bridge.ip or old_key != self.bridge.key) and self.bridge.ip and self.bridge.key:
                xbmc.log("[script.service.hue] IP or key changed, reconnecting...")
                self.bridge.connect()
            SETTINGS_CHANGED.clear()


class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

    def onSettingsChanged(self):
        xbmc.log("[script.service.hue] Settings changed")
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


class Timers(threading.Thread):
    def __init__(self, monitor, bridge, hue_service):
        self.monitor = monitor
        self.bridge = bridge
        self.hue_service = hue_service
        self.morning_time = convert_time(ADDON.getSettingString("morningTime"))
        self.stop_timers = threading.Event()  # Flag to stop the thread

        super().__init__()

    def run(self):
        self._set_daytime()
        self._task_loop()

    def stop(self):
        self.stop_timers.set()

    def _run_morning(self):
        cache_set("daytime", True)
        self.bridge.update_sunset()
        xbmc.log(f"[script.service.hue] run_morning(): new sunset: {self.bridge.sunset}")

    def _run_sunset(self):
        xbmc.log(f"[script.service.hue] in run_sunset(): Sunset. ")
        cache_set("daytime", False)
        self.hue_service.activate()

    def _set_daytime(self):
        now = datetime.now()

        if self.morning_time <= now.time() <= self.bridge.sunset:
            cache_set("daytime", True)
        else:
            cache_set("daytime", False)

    def _task_loop(self):

        while not self.monitor.abortRequested() and not self.stop_timers.is_set():

            now = datetime.now()
            self.morning_time = convert_time(ADDON.getSettingString("morningTime")) # Update morning time in case it has changed

            time_to_sunset = self._time_until(now, self.bridge.sunset)
            time_to_morning = self._time_until(now, self.morning_time)

            if time_to_sunset < time_to_morning:
                # Sunset is next
                wait_time = time_to_sunset
                xbmc.log(f"[script.service.hue] Timers: Sunset is next. wait_time: {wait_time}")
                if self.monitor.waitForAbort(wait_time):
                    break
                self._run_sunset()

            else:
                # Morning is next
                wait_time = time_to_morning
                xbmc.log(f"[script.service.hue] Timers: Morning is next. wait_time: {wait_time}")
                if self.monitor.waitForAbort(wait_time):
                    break
                self._run_morning()
        xbmc.log("[script.service.hue] Timers stopped")

    @staticmethod
    def _time_until(current, target):
        # Calculates remaining time from current to target
        now = datetime(1, 1, 1, current.hour, current.minute, current.second)
        then = datetime(1, 1, 1, target.hour, target.minute, target.second)
        return (then - now).seconds
