#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import traceback
from threading import Thread

import requests
import xbmc
import xbmcgui
from PIL import Image

from . import ADDON, MINIMUM_COLOR_DISTANCE, imageprocess, lightgroup
from . import PROCESS_TIMES, reporting, AMBI_RUNNING
from .kodiutils import notification
from .language import get_string as _
from .lightgroup import STATE_STOPPED, STATE_PAUSED, STATE_PLAYING, VIDEO
from .rgbxy import Converter, ColorHelper  # https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA, GamutB, GamutC


class AmbiGroup(lightgroup.LightGroup):
    def __init__(self, light_group_id, monitor, bridge):

        self.bridge = bridge
        self.light_group_id = light_group_id

        self.monitor = monitor
        self.state = STATE_STOPPED
        self.video_info_tag = xbmc.InfoTagVideo

        self.bridge_error500 = 0
        self.saved_light_states = {}

        self.image_process = imageprocess.ImageProcess()

        self.converterA = Converter(GamutA)
        self.converterB = Converter(GamutB)
        self.converterC = Converter(GamutC)
        self.helper = ColorHelper(GamutC)  # Gamut doesn't matter for this usage
        self.reload_settings()

        super().__init__(light_group_id, bridge, media_type=VIDEO)

    def reload_settings(self):
        #load generic settings
        super._reload_settings(self.light_group_id)

        if type(self) == AmbiGroup:
            #load ambigroup specific settings
            self.transition_time = int(ADDON.getSettingInt(f"group{self.light_group_id}_TransitionTime") / 100)  # This is given as a multiple of 100ms and defaults to 4 (400ms). transition_time:10 will make the transition last 1 second.
            self.force_on = ADDON.getSettingBool(f"group{self.light_group_id}_forceOn")
            self.disable_labs = ADDON.getSettingBool(f"group{self.light_group_id}_disableLabs")
            self.min_bri = ADDON.getSettingInt(f"group{self.light_group_id}_MinBrightness") * 255 / 100  # convert percentage to value 1-254
            self.max_bri = ADDON.getSettingInt(f"group{self.light_group_id}_MaxBrightness") * 255 / 100  # convert percentage to value 1-254
            self.saturation = ADDON.getSettingNumber(f"group{self.light_group_id}_Saturation")
            self.capture_size_x = ADDON.getSettingInt(f"group{self.light_group_id}_CaptureSize")
            self.resume_state = ADDON.getSettingBool(f"group{self.light_group_id}_ResumeState")
            self.resume_transition = ADDON.getSettingInt(f"group{self.light_group_id}_ResumeTransition") * 10  # convert seconds to multiple of 100ms

            if self.enabled and self.bridge.connected:
                self.ambi_lights = {}
                light_ids = ADDON.getSettingString(f"group{self.light_group_id}_Lights").split(",")
                index = 0

                if len(light_ids) > 0:
                    for L in light_ids:
                        gamut = self._get_light_gamut(self.bridge, L)
                        light = {L: {'gamut': gamut, 'prev_xy': (0, 0), "index": index}}
                        self.ambi_lights.update(light)
                        index = index + 1

            self.update_interval = ADDON.getSettingInt(f"group{self.light_group_id}_Interval") / 1000  # convert MS to seconds
            if self.update_interval == 0:
                self.update_interval = 0.1

    @staticmethod
    def _force_on(ambi_lights, bridge, saved_light_states):
        for L in ambi_lights:
            try:
                if not saved_light_states[L]['state']['on']:
                    xbmc.log("[script.service.hue] Forcing lights on")
                    bridge.lights[L].state(on=True, bri=1)
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue] Requests exception: {exc}")
                notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)

    def onAVStarted(self):
        self.state = STATE_PLAYING
        self.last_media_type = self._playback_type()
        xbmc.log(f"[script.service.hue] AmbiGroup[{self.light_group_id}] onPlaybackStarted. Group enabled: {self.enabled}, Bridge connected: {self.bridge.connected}, mediaType: {self.media_type}")

        if not self.enabled or not self.bridge.connected:
            return

        xbmc.log(f"[script.service.hue] AmbiGroup[{self.light_group_id}] onPlaybackStarted. play_behavior: {self.play_enabled}, media_type: {self.media_type} == playback_type: {self._playback_type()}")
        if self.play_enabled and self.media_type == self._playback_type() and self._playback_type() == VIDEO:
            try:
                self.video_info_tag = self.getVideoInfoTag()
            except (AttributeError, TypeError) as x:
                xbmc.log(f"[script.service.hue] AmbiGroup{self.light_group_id}: OnAV Started: Can't read infoTag")
                reporting.process_exception(x)
        else:
            self.video_info_tag = None

        if self.activation_check.validate(self.play_scene):
            xbmc.log(f"[script.service.hue] AmbiGroup[{self.light_group_id}] Running Play action")

            # Save light states
            #self.saved_light_states = self._get_and_save_light_states()

            # Stop effects if disable_labs is True
            #if self.disable_labs:
            #    self._stop_effects()

            # Force on lights if force_on is True
            if self.force_on:
                self._force_on(self.ambi_lights, self.bridge, self.saved_light_states)

            # Start the Ambi loop
            ambi_loop_thread = Thread(target=self._ambi_loop, name="_ambi_loop", daemon=True)
            ambi_loop_thread.start()

    def onPlayBackStopped(self):
        # always stop ambilight even if group is disabled or it'll run forever
        xbmc.log(f"[script.service.hue] In ambiGroup[{self.light_group_id}], onPlaybackStopped()")
        self.state = STATE_STOPPED
        AMBI_RUNNING.clear()

        if self.enabled:
            if self.resume_state:
                self._resume_all_light_states(self.saved_light_states)

            if self.disable_labs:
                self._resume_effects()

    def onPlayBackPaused(self):
        # always stop ambilight even if group is disabled or it'll run forever
        xbmc.log(f"[script.service.hue] In ambiGroup[{self.light_group_id}], onPlaybackPaused()")
        self.state = STATE_PAUSED
        AMBI_RUNNING.clear()

        if self.enabled:
            if self.resume_state:
                self._resume_all_light_states(self.saved_light_states)

            if self.disable_labs:
                self._resume_effects()

    def _ambi_loop(self):
        AMBI_RUNNING.set()
        cap = xbmc.RenderCapture()
        cap_image = bytes
        xbmc.log("[script.service.hue] _ambiLoop started")
        aspect_ratio = cap.getAspectRatio()

        self.capture_size_y = int(self.capture_size_x / aspect_ratio)
        expected_capture_size = self.capture_size_x * self.capture_size_y * 4  # size * 4 bytes - RGBA
        xbmc.log(f"[script.service.hue] aspect_ratio: {aspect_ratio}, Capture Size: ({self.capture_size_x},{self.capture_size_y}), expected_capture_size: {expected_capture_size}")

        cap.capture(self.capture_size_x, self.capture_size_y)  # start the capture process https://github.com/xbmc/xbmc/pull/8613#issuecomment-165699101

        for L in list(self.ambi_lights):
            self.ambi_lights[L].update(prev_xy=(0.0001, 0.0001))

        while not self.monitor.abortRequested() and AMBI_RUNNING.is_set() and self.hue_connection.connected:  # loop until kodi tells add-on to stop or video playing flag is unset.
            try:

                cap_image = cap.getImage()  # timeout to wait for OS in ms, default 1000

                if cap_image is None or len(cap_image) < expected_capture_size:
                    xbmc.log("[script.service.hue] capImage is none or < expected. captured: {}, expected: {}".format(len(cap_image), expected_capture_size))
                    self.monitor.waitForAbort(0.25)  # pause before trying again
                    continue  # no image captured, try again next iteration
                image = Image.frombytes("RGBA", (self.capture_size_x, self.capture_size_y), bytes(cap_image), "raw", "BGRA", 0, 1)  # Kodi always returns a BGRA image.

            except ValueError:
                xbmc.log(f"[script.service.hue] capImage: {len(cap_image)}")
                xbmc.log("[script.service.hue] Value Error")
                self.monitor.waitForAbort(0.25)
                continue  # returned capture is smaller than expected, but this happens when player is stopping so fail silently. give up this loop.

            colors = self.image_process.img_avg(image, self.min_bri, self.max_bri, self.saturation)
            for L in list(self.ambi_lights):
                t = Thread(target=self._update_hue_rgb, name="_update_hue_rgb", args=(colors['rgb'][0], colors['rgb'][1], colors['rgb'][2], L, self.transition_time, colors['bri']), daemon=True)
                t.start()

            self.monitor.waitForAbort(self.update_interval)  # seconds

        if not self.monitor.abortRequested():  # ignore writing average process time if Kodi is shutting down
            average_process_time = self._perf_average(PROCESS_TIMES)
            xbmc.log(f"[script.service.hue] Average process time: {average_process_time}")
            ADDON.setSettingString("average_process_time", str(average_process_time))
            xbmc.log("[script.service.hue] _ambiLoop stopped")

    def _update_hue_rgb(self, r, g, b, light, transition_time, bri):
        gamut = self.ambi_lights[light].get('gamut')
        prev_xy = self.ambi_lights[light].get('prev_xy')

        if gamut == "A":
            xy = self.converterA.rgb_to_xy(r, g, b)
        elif gamut == "B":
            xy = self.converterB.rgb_to_xy(r, g, b)
        else:
            xy = self.converterC.rgb_to_xy(r, g, b)

        xy = round(xy[0], 4), round(xy[1], 4)  # Hue has a max precision of 4 decimal points
        distance = self.helper.get_distance_between_two_points(XYPoint(xy[0], xy[1]), XYPoint(prev_xy[0], prev_xy[1]))  # only update hue if XY changed enough

        if distance > MINIMUM_COLOR_DISTANCE:
            response = self.bridge.make_api_request('PUT', f'lights/{light}/state', json={'xy': xy, 'bri': bri, 'transitiontime': int(transition_time)})
            if response is not None:
                self.ambi_lights[light].update(prev_xy=xy)
            elif response == 429 or response == 500:
                xbmc.log(f"[script.service.hue] AmbiGroup[{self.light_group_id}] _update_hue_rgb: {response}: Too Many Requests. Aborting request.")
                self._bridge_error500()
                notification(_("Hue Service"), _("Bridge overloaded, aborting"), icon=xbmcgui.NOTIFICATION_ERROR)
            elif response == 404:
                xbmc.log(f"[script.service.hue] AmbiGroup[{self.light_group_id}] Not Found")
                AMBI_RUNNING.clear()
                notification(header=_("Hue Service"), message=_(f"Error: Lights incompatible with Ambilight or not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                xbmc.log(f"[script.service.hue] AmbiGroup[{self.light_group_id}] RequestException Hue call fail")
                AMBI_RUNNING.clear()  # shut it down
                reporting.process_exception(response)

    def _bridge_error500(self):
        self.bridge_error500 = self.bridge_error500 + 1  # increment counter
        if self.bridge_error500 > 50 and ADDON.getSettingBool("show500Error"):
            AMBI_RUNNING.clear()  # shut it down
            stop_showing_error = xbmcgui.Dialog().yesno(_("Hue Bridge over capacity"), _("The Hue Bridge is over capacity. Increase refresh rate or reduce the number of Ambilights."), yeslabel=_("Do not show again"), nolabel=_("Ok"))
            if stop_showing_error:
                ADDON.setSettingBool("show500Error", False)
            self.bridge_error500 = 0

    def _stop_effects(self):
        self.saved_effect_sensors = self._get_effect_sensors()

        for sensor in self.saved_effect_sensors:
            xbmc.log(f"[script.service.hue] Stopping effect sensor {sensor}")
            self.bridge.sensors[sensor].state(status=0)

    def _resume_effects(self):
        if not hasattr(self, 'saved_effect_sensors'):
            return

        for sensor in self.saved_effect_sensors:
            xbmc.log(f"[script.service.hue] Resuming effect sensor {sensor}")
            self.bridge.sensors[sensor].state(status=1)

        self.saved_effect_sensors = None

    def _get_effect_sensors(self):
        # Map light/group IDs to associated effect sensor IDs
        lights = {}
        groups = {}

        # Find all sensor IDs for active Hue Labs effects
        all_sensors = self.bridge.sensors()
        effects = [effect_id
                   for effect_id, sensor in list(all_sensors.items())
                   if sensor['modelid'] == 'HUELABSVTOGGLE' and 'status' in sensor['state'] and sensor['state']['status'] == 1
                   ]

        # For each effect, find the linked lights or groups
        all_links = self.bridge.resourcelinks()
        for sensor in effects:
            sensor_links = [sensorLink
                            for link in list(all_links.values())
                            for sensorLink in link['links']
                            if '/sensors/' + sensor in link['links']
                            ]

            for link in sensor_links:

                i = link.split('/')[-1]
                if link.startswith('/lights/'):
                    lights.setdefault(i, set())
                    lights[i].add(sensor)
                elif link.startswith('/groups/'):
                    groups.setdefault(i, set())
                    groups[i].add(sensor)

        # For linked groups, find their associated lights
        all_groups = self.bridge.groups()
        for g, sensors in list(groups.items()):
            for i in all_groups[g]['lights']:
                lights.setdefault(i, set())
                lights[i] |= sensors

        if lights:
            xbmc.log(f'[script.service.hue] Found active Hue Labs effects on lights: {lights}')
            # Find all effect sensors that use the selected Ambilights.
            #
            # Only consider lights that are turned on, because enabling
            # an effect will also power on its lights.
            try:
                sensors = set([sensor
                               for sensor_id in list(self.ambi_lights.keys())
                               for sensor in lights[sensor_id]
                               if sensor_id in lights
                               and sensor_id in self.saved_light_states
                               and self.saved_light_states[sensor_id]['state']['on']
                               ])
                return sensors
            except KeyError:
                # Effects aren't running on any ambilights,
                xbmc.log("[script.service.hue] KeyError: Active Hue Labs aren't on any ambilights")
                return []

        else:
            xbmc.log('[script.service.hue] No active Hue Labs effects found')
            return []

    @staticmethod
    def _get_light_gamut(bridge, light):
        gamut = "C"  # default
        try:
            gamut = bridge.lights()[light]['capabilities']['control']['colorgamuttype']
            # xbmc.log("[script.service.hue] Light: {}, gamut: {}".format(l, gamut))
        except QhueException as exc:
            xbmc.log(f"[script.service.hue] Can't get gamut for light, defaulting to Gamut C: {light}, error: {exc}")
        except KeyError:
            xbmc.log(f"[script.service.hue] Unknown gamut type, unsupported light: {light}")
            notification(_("Hue Service"), _("Unknown colour gamut for light:") + f" {light}")
        except requests.RequestException as exc:
            xbmc.log(f"[script.service.hue] Get Light Gamut RequestsException: {exc}")
            notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)

        if gamut == "A" or gamut == "B" or gamut == "C":
            return gamut
        return "C"  # default to C if unknown gamut type

    @staticmethod
    def _perf_average(process_times):
        process_times = list(process_times)
        size = len(process_times)
        total = 0
        if size > 0:
            for x in process_times:
                total += x
            average_process_time = int(total / size * 1000)
            return f"{average_process_time} ms"
        return _("Unknown")

    def _get_and_save_light_states(self):
        response = self.bridge.make_api_request('GET', 'lights')
        if response is not None and 'data' in response:
            states = {}
            for light in response['data']:
                states[light['id']] = {
                    'on': light['on']['on'],
                    'brightness': light['dimming']['brightness'],
                    'color': light['color']['xy'],
                    'color_temperature': light['color_temperature']['mirek'] if 'mirek' in light['color_temperature'] else None,
                    'dynamics': light['dynamics']['status'],
                    'dynamics_speed': light['dynamics']['speed'],
                    'effects': light['effects']['status'],
                }
            return states
        else:
            xbmc.log(f"[script.service.hue] Failed to get light states.")
            return None

    def _resume_all_light_states(self, states):
        for light_id, state in states.items():
            data = {
                "type": "light",
                "on": {"on": state['on']},
                "dimming": {"brightness": state['brightness']},
                "color": {"xy": state['color']},
                "dynamics": {
                    "status": state['dynamics'],
                    "speed": state['dynamics_speed']
                },
                "effects": {"status": state['effects']}
            }
            if state['color_temperature'] is not None:
                data["color_temperature"] = {"mirek": state['color_temperature']}
            response = self.bridge.make_api_request('PUT', f'lights/{light_id}', json=data)
            if response is not None:
                xbmc.log(f"[script.service.hue] Light[{light_id}] state resumed successfully.")
            else:
                xbmc.log(f"[script.service.hue] Failed to resume Light[{light_id}] state.")
