"""Real-time ambilight via video frame capture and Hue light color matching.

Extends :class:`~lightgroup.LightGroup` to capture video frames, extract
dominant colors using PIL, convert RGB to CIE xy coordinates, and push color
updates to Hue lights in parallel using a :class:`~concurrent.futures.ThreadPoolExecutor`.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.


from threading import Thread
from concurrent.futures import ThreadPoolExecutor

import xbmc
import xbmcgui
from PIL import Image

from . import ADDON, MINIMUM_COLOR_DISTANCE, imageprocess, lightgroup
from . import PROCESS_TIMES, reporting, AMBI_RUNNING
from .kodiutils import notification, log
from .language import get_string as _
from .lightgroup import STATE_STOPPED, STATE_PAUSED, STATE_PLAYING, VIDEO
from .rgbxy import Converter, ColorHelper  # https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA, GamutB, GamutC


class AmbiGroup(lightgroup.LightGroup):
    """Ambilight group that captures video frames and updates Hue lights in real time.

    Overrides playback event handlers to start/stop a capture loop thread.
    Each frame is processed to extract average color, which is then pushed
    to all configured ambilight lights via the Hue API.

    Args:
        light_group_id: Numeric group identifier (typically 3 for ambilight).
        settings_monitor: Active :class:`~settings.SettingsMonitor` instance.
        bridge: Active :class:`~hue.Hue` instance for API calls.
    """

    def __init__(self, light_group_id, settings_monitor, bridge):

        self.bridge = bridge
        self.light_group_id = light_group_id
        self.settings_monitor = settings_monitor
        super().__init__(light_group_id, VIDEO, self.settings_monitor, self.bridge)

        self.capacity_error_count = 0
        self.saved_light_states = {}
        self.ambi_lights = {}

        self.image_process = imageprocess.ImageProcess()

        self.converterA = Converter(GamutA)
        self.converterB = Converter(GamutB)
        self.converterC = Converter(GamutC)
        self.helper = ColorHelper(GamutC)  # Gamut doesn't matter for distance calculation

    def onAVStarted(self):
        """Handle playback start: validate activation rules and start the ambilight capture loop.

        Fetches the configured ambilight lights, reads the video info tag, and
        spawns :meth:`_ambi_loop` on a daemon thread if activation rules pass.
        """
        self.state = STATE_PLAYING
        self.last_media_type = self._playback_type()
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled", False)

        if getattr(self.settings_monitor, f"group{self.light_group_id}_enabled", False) and self.bridge.connected:
            self._get_lights()
        else:
            return

        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] onPlaybackStarted. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}, mediaType: {self.media_type}")


        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] onPlaybackStarted. media_type: {self.media_type} == playback_type: {self._playback_type()}")
        if self.media_type == self._playback_type() and self._playback_type() == VIDEO:
            try:
                self.info_tag = self.getVideoInfoTag()
            except (AttributeError, TypeError) as exc:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup{self.light_group_id}: OnAV Started: Can't read infoTag")
                reporting.process_exception(exc)
        else:
            self.info_tag = None

        if self.activation_check.validate():
            log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Running Play action")
            self._get_and_save_light_states()

            ambi_loop_thread = Thread(target=self._ambi_loop, name="_ambi_loop", daemon=True)
            ambi_loop_thread.start()

    def onPlayBackStopped(self):
        """Handle playback stop: clear the ambilight running flag to terminate the capture loop.

        Always stops ambilight regardless of group enabled state to prevent
        the capture loop from running indefinitely.
        """
        log(f"[SCRIPT.SERVICE.HUE] In ambiGroup[{self.light_group_id}], onPlaybackStopped()")
        self.state = STATE_STOPPED
        AMBI_RUNNING.clear()
        self._resume_all_light_states()

    def onPlayBackPaused(self):
        """Handle playback pause: clear the ambilight running flag to terminate the capture loop.

        Always stops ambilight regardless of group enabled state to prevent
        the capture loop from running indefinitely.
        """
        log(f"[SCRIPT.SERVICE.HUE] In ambiGroup[{self.light_group_id}], onPlaybackPaused()")
        self.state = STATE_PAUSED
        AMBI_RUNNING.clear()
        self._resume_all_light_states()

    def _ambi_loop(self):
        """Main ambilight capture and update loop (runs on a daemon thread).

        Continuously captures video frames via :class:`xbmc.RenderCapture`,
        extracts average RGB color via :class:`~imageprocess.ImageProcess`,
        and submits color updates for each light to a thread pool. Runs until
        Kodi abort, ``AMBI_RUNNING`` is cleared, or the bridge disconnects.
        """
        AMBI_RUNNING.set()
        executor = ThreadPoolExecutor(max_workers=len(self.ambi_lights) * 2)
        capture = xbmc.RenderCapture()
        captured_image = None
        log("[SCRIPT.SERVICE.HUE] _ambiLoop started")
        aspect_ratio = capture.getAspectRatio()

        # These settings require restarting ambilight video to update:
        capture_width = getattr(self.settings_monitor, f"group{self.light_group_id}_capture_size")
        transition_time = getattr(self.settings_monitor, f"group{self.light_group_id}_transition_time")
        min_brightness = getattr(self.settings_monitor, f"group{self.light_group_id}_min_bri")
        max_brightness = getattr(self.settings_monitor, f"group{self.light_group_id}_max_bri")
        saturation = getattr(self.settings_monitor, f"group{self.light_group_id}_saturation")
        update_interval = getattr(self.settings_monitor, f"group{self.light_group_id}_update_interval")

        capture_height = int(capture_width / aspect_ratio)
        expected_capture_bytes = capture_width * capture_height * 4  # 4 bytes per pixel (RGBA)

        log(f"[SCRIPT.SERVICE.HUE] aspect_ratio: {aspect_ratio}, Capture Size: ({capture_width}, {capture_height}), expected_capture_bytes: {expected_capture_bytes}")

        capture.capture(capture_width, capture_height)  # start the capture process https://github.com/xbmc/xbmc/pull/8613#issuecomment-165699101

        for light_id in list(self.ambi_lights):
            self.ambi_lights[light_id].update(prev_xy=(0.0001, 0.0001))

        while not self.settings_monitor.abortRequested() and AMBI_RUNNING.is_set() and self.bridge.connected:
            try:

                captured_image = capture.getImage()

                if captured_image is None or len(captured_image) < expected_capture_bytes:
                    log("[SCRIPT.SERVICE.HUE] capImage is none or < expected. captured: {}, expected: {}".format(len(captured_image), expected_capture_bytes))
                    self.settings_monitor.waitForAbort(0.25)
                    continue
                image = Image.frombytes("RGBA", (capture_width, capture_height), bytes(captured_image), "raw", "BGRA", 0, 1)  # Kodi always returns a BGRA image.

            except ValueError:
                log(f"[SCRIPT.SERVICE.HUE] capImage: {len(captured_image)}")
                log("[SCRIPT.SERVICE.HUE] Value Error")
                self.settings_monitor.waitForAbort(0.25)
                continue  # returned capture is smaller than expected, but this happens when player is stopping so fail silently.

            colors = self.image_process.img_avg(image, min_brightness, max_brightness, saturation)
            for light_id in list(self.ambi_lights):
                executor.submit(self._update_hue_rgb, colors['rgb'][0], colors['rgb'][1], colors['rgb'][2], light_id, colors['bri'], transition_time)

            self.settings_monitor.waitForAbort(update_interval)

        executor.shutdown(wait=False)

        if not self.settings_monitor.abortRequested():
            average_process_time = self._perf_average(PROCESS_TIMES)
            log(f"[SCRIPT.SERVICE.HUE] Average process time: {average_process_time}")
            ADDON.setSettingString("average_process_time", str(average_process_time))
            log("[SCRIPT.SERVICE.HUE] _ambiLoop stopped")

    def _update_hue_rgb(self, red, green, blue, light_id, brightness, transition_time):
        """Convert RGB to CIE xy and update a single Hue light if the color changed enough.

        Uses the light's gamut-specific converter to map RGB to xy coordinates.
        Only sends an API request if the Euclidean distance from the previous
        xy value exceeds :data:`MINIMUM_COLOR_DISTANCE`.

        Args:
            red: Red channel value (0-255).
            green: Green channel value (0-255).
            blue: Blue channel value (0-255).
            light_id: Hue light resource ID.
            brightness: Hue brightness value (0-100).
            transition_time: Transition duration in milliseconds.
        """
        gamut = self.ambi_lights[light_id].get('gamut')
        previous_xy = self.ambi_lights[light_id].get('prev_xy')

        if gamut == "A":
            xy = self.converterA.rgb_to_xy(red, green, blue)
        elif gamut == "B":
            xy = self.converterB.rgb_to_xy(red, green, blue)
        else:
            xy = self.converterC.rgb_to_xy(red, green, blue)

        xy = round(xy[0], 4), round(xy[1], 4)  # Hue has a max precision of 4 decimal points
        color_distance = self.helper.get_distance_between_two_points(XYPoint(xy[0], xy[1]), XYPoint(previous_xy[0], previous_xy[1]))

        if color_distance > MINIMUM_COLOR_DISTANCE:
            request_body = {
                'type': 'light',
                'on': {
                    'on': True
                },
                'dimming': {
                    'brightness': brightness
                },
                'color': {
                    'xy': {
                        'x': xy[0],
                        'y': xy[1]
                    }
                },
                'dynamics': {
                    'duration': int(transition_time)
                }
            }
            response = self.bridge.make_api_request('PUT', f'light/{light_id}', json=request_body)

            if isinstance(response, dict):
                self.ambi_lights[light_id].update(prev_xy=xy)
            elif response == 429 or response == 500:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] _update_hue_rgb: {response}: Too Many Requests. Aborting request.")
                self.bridge_capacity_error()
                notification(_("Hue Service"), _("Bridge overloaded, stopping ambilight"), icon=xbmcgui.NOTIFICATION_ERROR)
            elif response == 404:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Not Found")
                AMBI_RUNNING.clear()
                notification(header=_("Hue Service"), message=_(f"ERROR: Light not found, it may have been deleted"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] RequestException Hue call fail")
                AMBI_RUNNING.clear()
                reporting.process_exception(response)

    def bridge_capacity_error(self):
        """Track bridge capacity errors and show a dialog after repeated failures.

        Increments an internal counter. After 50 consecutive errors, stops
        ambilight and prompts the user to increase the refresh rate or reduce
        the number of ambilight lights. The user can choose to suppress future errors.
        """
        self.capacity_error_count = self.capacity_error_count + 1
        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Bridge capacity error count: {self.capacity_error_count}")
        if self.capacity_error_count > 50 and self.settings_monitor.show500errors:
            AMBI_RUNNING.clear()
            stop_showing_error = xbmcgui.Dialog().yesno(_("Hue Bridge over capacity"), _("The Hue Bridge is over capacity. Increase refresh rate or reduce the number of Ambilights."), yeslabel=_("Do not show again"), nolabel=_("Ok"))
            if stop_showing_error:
                ADDON.setSettingBool("show500Error", False)
            self.capacity_error_count = 0

    @staticmethod
    def _get_light_gamut(bridge, light_id):
        """Fetch the color gamut type for a specific Hue light.

        Args:
            bridge: Active :class:`~hue.Hue` instance.
            light_id: Hue light resource ID.

        Returns:
            Gamut type string (``"A"``, ``"B"``, or ``"C"``), or ``404`` if
            the light was not found.
        """
        gamut = "C"  # default
        light_data = bridge.make_api_request("GET", f"light/{light_id}")
        if light_data == 404:
            log(f"[SCRIPT.SERVICE.HUE] _get_light_gamut: Light[{light_id}] not found or ID invalid")
            return 404
        elif light_data is not None and 'data' in light_data:
            for item in light_data['data']:
                if 'color' in item and 'gamut_type' in item['color']:
                    gamut = item['color']['gamut_type']
        if gamut not in ["A", "B", "C"]:
            gamut = "C"  # default to C if unknown gamut type
        return gamut

    @staticmethod
    def _perf_average(process_times):
        """Calculate the average frame processing time from the rolling buffer.

        Args:
            process_times: Deque of processing times in seconds.

        Returns:
            Formatted string like ``"12 ms"``, or ``"Unknown"`` if no data.
        """
        process_times = list(process_times)
        size = len(process_times)
        total = 0
        if size > 0:
            for x in process_times:
                total += x
            average_ms = int(total / size * 1000)
            return f"{average_ms} ms"
        return _("Unknown")

    def _get_and_save_light_states(self):
        """Fetch and save the current state of configured ambilight lights for later restoration.

        Only saves lights present in :attr:`ambi_lights`. Results are stored
        in :attr:`saved_light_states`.
        """
        self.saved_light_states = {}
        for light_id in self.ambi_lights:
            response = self.bridge.make_api_request('GET', f'light/{light_id}')
            if response is not None and 'data' in response:
                for light in response['data']:
                    self.saved_light_states[light['id']] = {
                        'on': light['on']['on'],
                        'brightness': light['dimming']['brightness'],
                        'color': light['color']['xy'],
                        'color_temperature': light['color_temperature']['mirek'] if 'mirek' in light.get('color_temperature', {}) else None,
                        'effects': light['effects']['status'] if 'effects' in light else None,
                    }
            else:
                log(f"[SCRIPT.SERVICE.HUE] Failed to get state for Light[{light_id}].")

    def _resume_all_light_states(self):
        """Restore previously saved light states via the Hue API.

        Only restores if ``group3_ResumeState`` is enabled and saved states exist.
        Uses ``group3_ResumeTransition`` for the transition duration.
        """
        if not self.settings_monitor.group3_resume_state or not self.saved_light_states:
            return

        for light_id, state in self.saved_light_states.items():
            data = {
                "type": "light",
                "on": {"on": state['on']},
                "dimming": {"brightness": state['brightness']},
                "color": {"xy": state['color']},
                "dynamics": {"duration": self.settings_monitor.group3_resume_transition},
            }
            if state['effects'] is not None:
                data["effects"] = {"status": state['effects']}
            if state['color_temperature'] is not None:
                data["color_temperature"] = {"mirek": state['color_temperature']}
            response = self.bridge.make_api_request('PUT', f'light/{light_id}', json=data)
            if response is not None:
                log(f"[SCRIPT.SERVICE.HUE] Light[{light_id}] state resumed successfully.")
            else:
                log(f"[SCRIPT.SERVICE.HUE] Failed to resume Light[{light_id}] state.")

    def _get_lights(self):
        """Fetch configured ambilight light IDs and their color gamuts from settings.

        Populates :attr:`ambi_lights` with a dict mapping light IDs to their
        gamut type and previous xy coordinates. Shows an error notification
        and disables the group if a light is no longer found on the bridge.
        """
        index = 0
        light_ids = getattr(self.settings_monitor, f"group{self.light_group_id}_lights")
        if len(light_ids) > 0:
            for light_id in light_ids:
                gamut = self._get_light_gamut(self.bridge, light_id)
                if gamut == 404:
                    notification(header=_("Hue Service"), message=_(f"ERROR: Light not found, it may have been deleted"), icon=xbmcgui.NOTIFICATION_ERROR)
                    AMBI_RUNNING.clear()
                    ADDON.setSettingString(f"group{self.light_group_id}_Lights", "-1")
                    ADDON.setSettingString(f"group{self.light_group_id}_LightNames", _("Not selected"))
                else:
                    light = {light_id: {'gamut': gamut, 'prev_xy': (0, 0), "index": index}}
                    self.ambi_lights.update(light)
                    index = index + 1
        log(f"[SCRIPT.SERVICE.HUE] AmbiGroup[{self.light_group_id}] Lights: {self.ambi_lights}")
