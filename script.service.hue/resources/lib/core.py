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
from . import ambigroup, lightgroup, kodiutils
from .hueconnection import HueConnection
from .kodiutils import validate_settings, notification, cache_set, cache_get
from .language import get_string as _
from .huev2 import HueAPIv2


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
        hue_connection = HueConnection(self.monitor, silent=True, discover=True)
        if hue_connection.connected:
            xbmc.log("[script.service.hue] Found bridge. Starting service.")
            ADDON.openSettings()
            service = HueService(self.monitor)
            service.run()
        else:
            ADDON.openSettings()

    def scene_select(self, light_group, action):
        xbmc.log(f"[script.service.hue] sceneSelect: light_group: {light_group}, action: {action}")
        bridge = HueAPIv2(self.monitor)
        if bridge.connected:
            bridge.configure_scene(light_group, action)
        else:
            xbmc.log("[script.service.hue] No bridge found. sceneSelect cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    def ambi_light_select(self, light_group):
        hue_connection = HueConnection(self.monitor, silent=True, discover=False)
        if hue_connection.connected:
            hue_connection.configure_ambilights(light_group)
        else:
            xbmc.log("[script.service.hue] No bridge found. Select ambi lights cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))


class HueService:
    def __init__(self, monitor):
        self.monitor = monitor
        self.hue_connection = HueConnection(monitor, discover=False)
        self.bridge = HueAPIv2(monitor)
        self.light_groups = []
        self.timers = None
        self.service_enabled = True
        cache_set("service_enabled", True)

    def run(self):
        if not (self.bridge.connected and self.hue_connection.connected):
            xbmc.log("[script.service.hue] Not connected, exiting...")
            return

        # Initialize light groups and timers only if the connection is successful
        self.light_groups = self.initialize_light_groups()
        self.timers = Timers(self.monitor, self.bridge, self)
        self.timers.start()

        # Track the previous state of the service
        prev_service_enabled = self.service_enabled

        while not self.monitor.abortRequested():
            # Update the current state of the service
            self.service_enabled = cache_get("service_enabled")

            if self.service_enabled:
                # If the service was previously disabled and is now enabled, activate light groups
                if not prev_service_enabled:
                    self.activate()

                self._process_actions()
                self._reload_settings_if_needed()
            else:
                AMBI_RUNNING.clear()

            # Update the previous state for the next iteration
            prev_service_enabled = self.service_enabled

            if self.monitor.waitForAbort(1):
                break

        xbmc.log("[script.service.hue] Process exiting...")

    def initialize_light_groups(self):
        # Initialize light groups
        return [
            lightgroup.LightGroup(0, self.hue_connection, self.bridge, lightgroup.VIDEO),
            lightgroup.LightGroup(1, self.hue_connection, self.bridge, lightgroup.AUDIO),
            ambigroup.AmbiGroup(3, self.hue_connection)
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
            for group in self.light_groups:
                group.reload_settings()
            self.bridge.reload_settings()
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
        self.morning_time = datetime.datetime.strptime(ADDON.getSettingString("morningTime"), "%H:%M").time()
        self._set_daytime()
        super().__init__()

    def run(self):
        self._task_loop()

    def _run_morning(self):
        cache_set("daytime", True)
        self.bridge.update_sunset()
        xbmc.log(f"[script.service.hue] run_morning(): new sunset: {self.bridge.sunset}")

    def _run_sunset(self):
        xbmc.log(f"[script.service.hue] in run_sunset(): Sunset. ")
        cache_set("daytime", False)
        self.hue_service.activate()

    def _set_daytime(self):
        now = datetime.datetime.now()

        if self.morning_time <= now.time() <= self.bridge.sunset:
            cache_set("daytime", True)
        else:
            cache_set("daytime", False)

    def _task_loop(self):

        while not self.monitor.abortRequested():

            now = datetime.datetime.now()
            self.morning_time = datetime.datetime.strptime(ADDON.getSettingString("morningTime"), "%H:%M").time()

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

    @staticmethod
    def _time_until(current, target):
        # Calculates remaining time from current to target
        now = datetime.datetime(1, 1, 1, current.hour, current.minute, current.second)
        then = datetime.datetime(1, 1, 1, target.hour, target.minute, target.second)
        return (then - now).seconds
