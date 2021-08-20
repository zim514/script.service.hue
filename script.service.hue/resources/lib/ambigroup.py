from threading import Thread

import requests
import xbmc
import xbmcgui
from PIL import Image

from resources.lib import kodihue, PROCESS_TIMES, reporting, globals
from resources.lib.language import get_string as _
from . import ADDON
from . import imageprocess
from . import kodigroup
from . import MINIMUM_COLOR_DISTANCE

from .kodigroup import STATE_STOPPED, STATE_PAUSED, STATE_PLAYING

from .qhue import QhueException
from .rgbxy import Converter, ColorHelper  # https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA, GamutB, GamutC


class AmbiGroup(kodigroup.KodiGroup):
    def __init__(self, kgroup_id, bridge, monitor, flash=False, initial_state=STATE_STOPPED):

        self.kgroup_id = kgroup_id
        self.bridge = bridge
        self.monitor = monitor
        self.group0 = self.bridge.groups[0]
        self.bridge_error500 = 0
        self.state = initial_state

        self.image_process = imageprocess.ImageProcess()

        self.converterA = Converter(GamutA)
        self.converterB = Converter(GamutB)
        self.converterC = Converter(GamutC)
        self.helper = ColorHelper(GamutC)

        self.enabled = ADDON.getSettingBool("group{}_enabled".format(self.kgroup_id))

        self.transition_time = int(ADDON.getSettingInt("group{}_TransitionTime".format(self.kgroup_id)) / 100)  # This is given as a multiple of 100ms and defaults to 4 (400ms). transitiontime:10 will make the transition last 1 second.
        self.force_on = ADDON.getSettingBool("group{}_forceOn".format(self.kgroup_id))
        self.disable_labs = ADDON.getSettingBool("group{}_disableLabs".format(self.kgroup_id))
        self.min_bri = ADDON.getSettingInt("group{}_MinBrightness".format(self.kgroup_id)) * 255 / 100  # convert percentage to value 1-254
        self.max_bri = ADDON.getSettingInt("group{}_MaxBrightness".format(self.kgroup_id)) * 255 / 100  # convert percentage to value 1-254
        self.saturation = ADDON.getSettingNumber("group{}_Saturation".format(self.kgroup_id))
        self.capture_size_x = ADDON.getSettingInt("group{}_CaptureSize".format(self.kgroup_id))
        self.resume_state = ADDON.getSettingBool("group{}_ResumeState".format(self.kgroup_id))
        self.resume_transition = ADDON.getSettingInt("group{}_ResumeTransition".format(self.kgroup_id)) * 10  # convert seconds to multiple of 100ms

        self.update_interval = ADDON.getSettingInt("group{}_Interval".format(self.kgroup_id)) / 1000  # convert MS to seconds
        if self.update_interval == 0:
            self.update_interval = 0.002

        self.ambiLights = {}
        light_ids = ADDON.getSetting("group{}_Lights".format(self.kgroup_id)).split(",")
        index = 0
        for L in light_ids:
            gamut = kodihue.get_light_gamut(self.bridge, L)
            light = {L: {'gamut': gamut, 'prevxy': (0, 0), "index": index}}
            self.ambiLights.update(light)
            index = index + 1

        if flash:
            self.flash()

        super(xbmc.Player).__init__()

    @staticmethod
    def _force_on(ambi_lights, bridge, saved_light_states):
        for L in ambi_lights:
            try:
                if not saved_light_states[L]['state']['on']:
                    xbmc.log("[script.service.hue] Forcing lights on".format(saved_light_states))
                    bridge.lights[L].state(on=True, bri=1)
            except QhueException as exc:
                xbmc.log("[script.service.hue] Force On Hue call fail: {}: {}".format(exc.type_id, exc.message))
                reporting.process_exception(exc)

    def onAVStarted(self):

        xbmc.log("Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.playbackType(): {}".format(self.enabled, self.isPlayingVideo(), self.isPlayingAudio(), self.playback_type()))
        xbmc.log("Ambilight Settings: Interval: {}, transitionTime: {}".format(self.update_interval, self.transition_time))

        self.state = STATE_PLAYING

        # save light state
        self.saved_light_states = kodihue.get_light_states(self.ambiLights, self.bridge)

        self.video_info_tag = self.getVideoInfoTag()
        if self.isPlayingVideo():
            if self.enabled and self.check_active_time() and self.check_video_activation(self.video_info_tag):

                if self.disable_labs:
                    self._stop_effects()

                if self.force_on:
                    self._force_on(self.ambiLights, self.bridge, self.saved_light_states)

                globals.AMBI_RUNNING.set()
                ambi_loop_thread = Thread(target=self._ambi_loop, name="_ambi_loop")
                ambi_loop_thread.daemon = True
                ambi_loop_thread.start()

    def onPlayBackStopped(self):
        xbmc.log("[script.service.hue] In ambiGroup[{}], onPlaybackStopped()".format(self.kgroup_id))
        self.state = STATE_STOPPED
        globals.AMBI_RUNNING.clear()

        if self.disable_labs:
            self._resume_effects()

        if self.resume_state:
            self._resume_light_state()

    def onPlayBackPaused(self):
        xbmc.log("[script.service.hue] In ambiGroup[{}], onPlaybackPaused()".format(self.kgroup_id))
        self.state = STATE_PAUSED
        globals.AMBI_RUNNING.clear()

        if self.disable_labs:
            self._resume_effects()

        if self.resume_state:
            self._resume_light_state()

    def _resume_light_state(self):
        xbmc.log("[script.service.hue] Resuming light state")
        for L in self.saved_light_states:
            xy = self.saved_light_states[L]['state']['xy']
            bri = self.saved_light_states[L]['state']['bri']
            on = self.saved_light_states[L]['state']['on']
            xbmc.log("[script.service.hue] Resume state: Light: {}, xy: {}, bri: {}, on: {},transition time: {}".format(L, xy, bri, on, self.resume_transition))
            try:
                self.bridge.lights[L].state(xy=xy, bri=bri, on=on, transitiontime=self.resume_transition)
            except QhueException as exc:
                if exc.type_id == 201:  # 201 Param not modifiable because light is off error. 901: internal hue bridge error.
                    pass
                else:
                    xbmc.log("[script.service.hue] resumeLightState: Hue call fail: {}: {}".format(exc.type_id, exc.message))
                    reporting.process_exception(exc)

    def _ambi_loop(self):

        cap = xbmc.RenderCapture()
        xbmc.log("[script.service.hue] _ambiLoop started")
        aspect_ratio = cap.getAspectRatio()

        self.capture_size_y = int(self.capture_size_x / aspect_ratio)
        expected_capture_size = self.capture_size_x * self.capture_size_y * 4  # size * 4 bytes - RGBA
        xbmc.log("[script.service.hue] aspect_ratio: {}, Capture Size: ({},{}), expected_capture_size: {}".format(aspect_ratio, self.capture_size_x, self.capture_size_y, expected_capture_size))

        for L in list(self.ambiLights):
            self.ambiLights[L].update(prevxy=(0.0001, 0.0001))

        try:
            while not self.monitor.abortRequested() and globals.AMBI_RUNNING.is_set():  # loop until kodi tells add-on to stop or video playing flag is unset.
                try:
                    cap.capture(self.capture_size_x, self.capture_size_y)  # async capture request to underlying OS
                    cap_image = cap.getImage()  # timeout to wait for OS in ms, default 1000

                    if cap_image is None or len(cap_image) < expected_capture_size:
                        # xbmc.log("[script.service.hue] capImage is none or < expected. captured: {}, expected: {}".format(len(capImage), expected_capture_size))
                        xbmc.sleep(250)  # pause before trying again
                        continue  # no image captured, try again next iteration
                    image = Image.frombytes("RGBA", (self.capture_size_x, self.capture_size_y), bytes(cap_image), "raw", "BGRA", 0, 1) #Kodi always returns a BGRA image.

                except ValueError:
                    xbmc.log("[script.service.hue] capImage: {}".format(len(cap_image)))
                    xbmc.log("[script.service.hue] Value Error")
                    self.monitor.waitForAbort(0.25)
                    continue  # returned capture is  smaller than expected, but this happens when player is stopping so fail silently. give up this loop.
                except Exception as exc:
                    xbmc.log("[script.service.hue] Capture exception")
                    reporting.process_exception(exc)
                    self.monitor.waitForAbort(0.25)
                    continue

                colors = self.image_process.img_avg(image, self.min_bri, self.max_bri, self.saturation)
                for L in list(self.ambiLights):
                    x = Thread(target=self._update_hue_rgb, name="updateHue", args=(colors['rgb'][0], colors['rgb'][1], colors['rgb'][2], L, self.transition_time, colors['bri']))
                    x.daemon = True
                    x.start()

                # if not CACHE.get("script.service.hue.service_enabled"):
                #     xbmc.log("[script.service.hue] Service disabled, stopping Ambilight")
                #     globals.AMBI_RUNNING.clear()
                self.monitor.waitForAbort(self.update_interval)  # seconds

            average_process_time = kodihue.perf_average(PROCESS_TIMES)
            xbmc.log("[script.service.hue] Average process time: {}".format(average_process_time))
            self.capture_size_x = ADDON.setSetting("average_process_time", str(average_process_time))

        except Exception as exc:
            xbmc.log("[script.service.hue] Exception in _ambiLoop")
            reporting.process_exception(exc)
        xbmc.log("[script.service.hue] _ambiLoop stopped")

    def _update_hue_rgb(self, r, g, b, light, transitionTime, bri):
        gamut = self.ambiLights[light].get('gamut')
        prev_xy = self.ambiLights[light].get('prev_xy')

        if gamut == "A":
            converter = self.converterA
        elif gamut == "B":
            converter = self.converterB
        elif gamut == "C":
            converter = self.converterC

        xy = converter.rgb_to_xy(r, g, b)
        xy = round(xy[0], 3), round(xy[1], 3)  # Hue has a max precision of 4 decimal points, but three is enough
        distance = self.helper.get_distance_between_two_points(XYPoint(xy[0], xy[1]), XYPoint(prev_xy[0], prev_xy[1]))  # only update hue if XY changed enough

        if distance > MINIMUM_COLOR_DISTANCE:
            try:
                self.bridge.lights[light].state(xy=xy, bri=bri, transitiontime=int(transitionTime))
                self.ambiLights[light].update(prevxy=xy)
            except QhueException as exc:
                if exc.type_id == 201:  # 201 Param not modifiable because light is off error. 901: internal hue bridge error.
                    pass
                elif exc.type_id == 500 or exc.type_id == 901:  # or exc == 500:  # bridge internal error
                    xbmc.log("[script.service.hue] Bridge internal error: {}".format(exc))
                    self._bridge_error500()
                else:
                    xbmc.log("[script.service.hue] Ambi: QhueException Hue call fail: {}: {}".format(exc.type_id, exc.message))
                    reporting.process_exception(exc)

            except requests.RequestException as exc:
                xbmc.log("[script.service.hue] Ambi: RequestException: {}".format(exc))
                self._bridge_error500()
            except KeyError:
                xbmc.log("[script.service.hue] Ambi: KeyError, light not found")

    def _bridge_error500(self):

        self.bridge_error500 = self.bridge_error500 + 1  # increment counter
        if self.bridge_error500 > 100 and ADDON.getSettingBool("show500Error"):
            stop_showing_error = xbmcgui.Dialog().yesno(_("Hue Bridge over capacity"), _("The Hue Bridge is over capacity. Increase refresh rate or reduce the number of Ambilights."), yeslabel=_("Do not show again"), nolabel=_("Ok"))

            if stop_showing_error:
                ADDON.setSettingBool("show500Error", False)
            self.bridge_error500 = 0

    def _stop_effects(self):
        self.savedEffectSensors = self._get_effect_sensors()

        for sensor in self.savedEffectSensors:
            xbmc.log("[script.service.hue] Stopping effect sensor {}".format(sensor))
            self.bridge.sensors[sensor].state(status=0)

    def _resume_effects(self):
        if not hasattr(self, 'savedEffectSensors'):
            return

        for sensor in self.savedEffectSensors:
            xbmc.log("[script.service.hue] Resuming effect sensor {}".format(sensor))
            self.bridge.sensors[sensor].state(status=1)

        self.savedEffectSensors = None

    def _get_effect_sensors(self):
        # Map light/group IDs to associated effect sensor IDs
        lights = {}
        groups = {}

        # Find all sensor IDs for active Hue Labs effects
        all_sensors = self.bridge.sensors()
        effects = [id
                   for id, sensor in list(all_sensors.items())
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
            xbmc.log('[script.service.hue] Found active Hue Labs effects on lights: {}'.format(lights))
        else:
            xbmc.log('[script.service.hue] No active Hue Labs effects found')
            return []

        # Find all effect sensors that use the selected Ambilights.
        #
        # Only consider lights that are turned on, because enabling
        # an effect will also power on its lights.
        return set([sensor
                    for i in list(self.ambiLights.keys())
                    if i in lights
                    and i in self.saved_light_states
                    and self.saved_light_states[i]['state']['on']
                    for sensor in lights[i]
                    ])
