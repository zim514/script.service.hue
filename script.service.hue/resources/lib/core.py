"""Service dispatcher, main loop, command handling, and scheduled timers.

This module is the central coordinator for the Hue service. It contains:

- :func:`core_dispatcher` — entry point that routes RunScript commands or starts the service.
- :class:`CommandHandler` — handles ``discover``, ``sceneSelect``, and ``ambiLightSelect`` commands
  invoked via Kodi's ``RunScript()`` from addon settings.
- :class:`HueService` — main 1-second polling loop managing bridge connection, light groups, and actions.
- :class:`Timers` — daemon thread that triggers morning/sunset transitions.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.


import sys
import threading
from datetime import datetime, timedelta, date


from . import ADDON, AMBI_RUNNING, BRIDGE_SETTINGS_CHANGED, KODIVERSION, ADDONVERSION
from . import lightgroup, ambigroup, settings
from .hue import Hue
from .kodiutils import notification, cache_set, cache_get, log
from .language import get_string as _


def core_dispatcher():
    """Entry point for the service. Routes RunScript commands or starts the main service loop.

    When called with arguments via Kodi's ``RunScript()`` (e.g. from addon
    settings buttons for ``discover``, ``sceneSelect``, ``ambiLightSelect``),
    delegates to :class:`CommandHandler`. When called without arguments (normal
    service startup), starts :class:`HueService` as the persistent background service.
    """
    settings_monitor = settings.SettingsMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        command_args = sys.argv[2:]

        command_handler = CommandHandler(settings_monitor)
        command_handler.handle_command(command, *command_args)
    else:
        service = HueService(settings_monitor)
        service.run()


class CommandHandler:
    """Routes Kodi RunScript commands to their respective handler methods.

    These commands are triggered by ``RunScript()`` calls in addon settings
    (e.g. the "Discover Bridge" button calls ``RunScript(script.service.hue, discover)``).

    Supported commands:
        - ``discover`` — initiate Hue Bridge discovery.
        - ``sceneSelect`` — open scene configuration for a light group + action.
        - ``ambiLightSelect`` — open ambilight light selection for a light group.

    Args:
        settings_monitor: Active :class:`~settings.SettingsMonitor` instance.
    """

    def __init__(self, settings_monitor):
        self.settings_monitor = settings_monitor
        self.commands = {
            "discover": self.discover,
            "sceneSelect": self.scene_select,
            "ambiLightSelect": self.ambi_light_select
        }

    def handle_command(self, command, *args):
        """Dispatch a RunScript command to the appropriate handler.

        Args:
            command: Command name string (from ``sys.argv[1]``).
            *args: Additional arguments forwarded to the handler.

        Raises:
            RuntimeError: If the command is not recognized.
        """
        log(f"[SCRIPT.SERVICE.HUE] Started with {command}, Kodi: {KODIVERSION}, Addon: {ADDONVERSION},  Python: {sys.version}")
        command_func = self.commands.get(command)

        if command_func:
            command_func(*args)
        else:
            log(f"[SCRIPT.SERVICE.HUE] Unknown command: {command}")
            raise RuntimeError(f"Unknown Command: {command}")

    def discover(self):
        """Initiate Hue Bridge discovery and open addon settings on completion."""
        bridge = Hue(self.settings_monitor, discover=True)
        if bridge.connected:
            log("[SCRIPT.SERVICE.HUE] Found bridge. Opening settings.")
            ADDON.openSettings()

        else:
            log("[SCRIPT.SERVICE.HUE] No bridge found. Opening settings.")
            ADDON.openSettings()

    def scene_select(self, light_group_id, action):
        """Open scene configuration UI for a specific light group and action.

        Args:
            light_group_id: The light group ID (``"0"`` for video, ``"1"`` for audio).
            action: The playback action (``"play"``, ``"pause"``, or ``"stop"``).
        """
        log(f"[SCRIPT.SERVICE.HUE] sceneSelect: light_group: {light_group_id}, action: {action}")
        bridge = Hue(self.settings_monitor)
        if bridge.connected:
            bridge.configure_scene(light_group_id, action)
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge found. sceneSelect cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))

    def ambi_light_select(self, light_group_id):
        """Open ambilight light selection UI for a specific light group.

        Args:
            light_group_id: The ambilight group ID (typically ``"3"``).
        """
        bridge = Hue(self.settings_monitor)
        if bridge.connected:
            bridge.configure_ambilights(light_group_id)
        else:
            log("[SCRIPT.SERVICE.HUE] No bridge found. Select ambi lights cancelled.")
            notification(_("Hue Service"), _("Check Hue Bridge configuration"))


class HueService:
    """Main background service that polls once per second and coordinates light groups.

    Responsibilities:
        - Monitors bridge connectivity and reconnects when settings change.
        - Processes cached action commands from the plugin UI.
        - Manages :class:`Timers` for sunrise/sunset scheduling.
        - Activates light groups when the service transitions from disabled to enabled.

    Args:
        settings_monitor: Active :class:`~settings.SettingsMonitor` instance.
    """

    def __init__(self, settings_monitor):
        self.settings_monitor = settings_monitor
        self.bridge = Hue(settings_monitor)
        self.light_groups = []
        self.timers = None
        self.service_enabled = True
        cache_set("service_enabled", True)

    def run(self):
        """Execute the main service loop (blocking, runs until Kodi abort).

        Polls once per second to:
        - Check for bridge setting changes and reconnect if needed.
        - Process queued action commands from the plugin UI.
        - Re-activate light groups when the service is re-enabled.
        - Manage timer thread lifecycle based on bridge connectivity.
        """
        log(f"[SCRIPT.SERVICE.HUE] Starting Hue Service, Kodi: {KODIVERSION}, Addon: {ADDONVERSION},  Python: {sys.version}")
        self.light_groups = self.initialize_light_groups()
        self.timers = Timers(self.settings_monitor, self.bridge, self)

        if self.bridge.connected:
            self.timers.start()

        previous_service_enabled = self.service_enabled

        while not self.settings_monitor.abortRequested(): # main loop, once per second
            self.service_enabled = cache_get("service_enabled")

            if BRIDGE_SETTINGS_CHANGED.is_set():
                self.bridge.connect()
                BRIDGE_SETTINGS_CHANGED.clear()

            self._process_action()

            if self.service_enabled:
                # Re-activate light groups when transitioning from disabled -> enabled
                if not previous_service_enabled and self.bridge.connected:
                    self.activate()
            else:
                AMBI_RUNNING.clear()

            if not self.bridge.connected and self.timers.is_alive():
                self.timers.stop()

            if self.bridge.connected and not self.timers.is_alive():
                self.timers = Timers(self.settings_monitor, self.bridge, self)
                self.timers.start()

            previous_service_enabled = self.service_enabled

            if self.settings_monitor.waitForAbort(1):
                break

        log("[SCRIPT.SERVICE.HUE] Abort requested...")

    def initialize_light_groups(self):
        """Create and return the three light group instances.

        Returns:
            List containing Video (ID 0), Audio (ID 1), and Ambilight (ID 3) groups.
        """
        return [
            lightgroup.LightGroup(0, lightgroup.VIDEO, self.settings_monitor, self.bridge),
            lightgroup.LightGroup(1, lightgroup.AUDIO, self.settings_monitor, self.bridge),
            ambigroup.AmbiGroup(3, self.settings_monitor, self.bridge)
        ]

    def activate(self):
        """Trigger the play action on all enabled light groups.

        Called at sunset and when the service is re-enabled via the Actions menu.
        """
        log(f"[SCRIPT.SERVICE.HUE] Activating scenes")

        for group in self.light_groups:
            if ADDON.getSettingBool(f"group{group.light_group_id}_enabled"):
                group.activate()

    def _process_action(self):
        """Process a pending action command from the window-property cache.

        Actions are stored as ``(action_name, light_group_id)`` tuples by the
        plugin menu. The light group ID is 1-indexed in the cache, so it is
        decremented to match the 0-indexed ``light_groups`` list.
        """
        action = cache_get("action")

        if action:
            action_name = action[0]
            action_light_group_index = int(action[1]) - 1
            log(f"[SCRIPT.SERVICE.HUE] Action command: {action}, action_name: {action_name}, action_light_group_index: {action_light_group_index}")

            self.light_groups[action_light_group_index].run_action(action_name)

            cache_set("action", None)


class Timers(threading.Thread):
    """Daemon thread that triggers morning and sunset transitions.

    Calculates the time until the next morning or sunset event and sleeps until
    that moment. At morning, updates the daytime flag and fetches the new sunset
    time. At sunset, clears the daytime flag and optionally activates light scenes.

    Args:
        settings_monitor: Active :class:`~settings.SettingsMonitor` instance.
        bridge: Active :class:`~hue.Hue` instance (for sunset time updates).
        hue_service: Parent :class:`HueService` (for scene activation at sunset).
    """

    def __init__(self, settings_monitor, bridge, hue_service):
        self.settings_monitor = settings_monitor
        self.bridge = bridge
        self.hue_service = hue_service
        self.morning_time = self.settings_monitor.morning_time
        self.stop_timers = threading.Event()

        super().__init__()

    def run(self):
        """Thread entry point: set initial daytime state, then enter the timer loop."""
        self._set_daytime()
        self._task_loop()

    def stop(self):
        """Signal the timer thread to stop."""
        self.stop_timers.set()

    def _run_morning(self):
        """Handle the morning transition: set daytime flag and refresh sunset time."""
        cache_set("daytime", True)
        self.bridge.update_sunset()
        log(f"[SCRIPT.SERVICE.HUE] run_morning(): new sunset: {self.bridge.sunset}")

    def _run_sunset(self):
        """Handle the sunset transition: clear daytime flag and optionally activate scenes."""
        log(f"[SCRIPT.SERVICE.HUE] in run_sunset(): Sunset. ")
        cache_set("daytime", False)
        if self.settings_monitor.force_on_sunset:
            self.hue_service.activate()


    def _set_daytime(self):
        """Calculate and cache the initial daytime state based on current time, morning time, and sunset."""
        now = datetime.now()
        log(f"[SCRIPT.SERVICE.HUE] _set_daytime(): Morning Time: {self.morning_time}, Now: {now.time()}, bridge.sunset: {self.bridge.sunset}, Sunset offset: {self.settings_monitor.sunset_offset}")

        sunset_datetime = datetime.combine(datetime.today(), self.bridge.sunset)
        sunset_with_offset = sunset_datetime + timedelta(minutes=self.settings_monitor.sunset_offset)

        if self.morning_time <= now.time() < sunset_with_offset.time():
            is_daytime = True
        else:
            is_daytime = False
        cache_set("daytime", is_daytime)
        log(f"[SCRIPT.SERVICE.HUE] in _set_daytime(): Sunset with offset: {sunset_with_offset}, Daytime: {is_daytime} ")

    def _task_loop(self):
        """Sleep until the next morning or sunset event, then execute the corresponding handler.

        Loops continuously, alternating between morning and sunset events based
        on which is chronologically next. Exits on Kodi abort or when
        :meth:`stop` is called.
        """

        while not self.settings_monitor.abortRequested() and not self.stop_timers.is_set(): #todo: Update timers if sunset offset changes.

            now = datetime.now() #+ timedelta(seconds=5)
            today = date.today()

            morning_datetime = datetime.combine(today, self.settings_monitor.morning_time)
            sunset_datetime = datetime.combine(today, self.bridge.sunset) + timedelta(minutes=self.settings_monitor.sunset_offset)

            if sunset_datetime < now:
                sunset_datetime += timedelta(days=1)
            if morning_datetime < now:
                morning_datetime += timedelta(days=1)

            seconds_to_sunset = (sunset_datetime - now).total_seconds()
            seconds_to_morning = (morning_datetime - now).total_seconds()

            log(f"[SCRIPT.SERVICE.HUE] Time to sunset: {seconds_to_sunset}, Time to morning: {seconds_to_morning}")

            if seconds_to_morning < seconds_to_sunset:
                log(f"[SCRIPT.SERVICE.HUE] Timers: Morning is next. wait_time: {seconds_to_morning}")
                if self.settings_monitor.waitForAbort(seconds_to_morning):
                    break
                self._run_morning()
            else:
                log(f"[SCRIPT.SERVICE.HUE] Timers: Sunset is next. wait_time: {seconds_to_sunset}")
                if self.settings_monitor.waitForAbort(seconds_to_sunset):
                    break
                self._run_sunset()
        log("[SCRIPT.SERVICE.HUE] Timers stopped")
