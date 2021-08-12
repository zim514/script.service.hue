from threading import Thread, Event

import requests
import xbmc
import xbmcgui
from PIL import Image

from resources.lib import kodihue, PROCESS_TIMES, cache, reporting
from resources.lib.language import get_string as _
from . import ADDON
from . import MINIMUM_COLOR_DISTANCE
from . import imageprocess
from . import kodigroup
from .kodigroup import STATE_STOPPED, STATE_PAUSED, STATE_PLAYING
from .kodisettings import settings_storage
from .qhue import QhueException
from .rgbxy import Converter, ColorHelper  # https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA, GamutB, GamutC


class AmbiGroup(kodigroup.KodiGroup):
    def __init__(self, kgroupID, bridge, monitor, flash=False):

        self.kgroupID = kgroupID
        self.bridge = bridge
        self.monitor = monitor
        self.group0 = self.bridge.groups[0]
        self.bridgeError500 = 0

        self.ambiRunning = Event()
        self.imageProcess = imageprocess.ImageProcess()

        self.converterA = Converter(GamutA)
        self.converterB = Converter(GamutB)
        self.converterC = Converter(GamutC)
        self.helper = ColorHelper(GamutC)

        self.enabled = ADDON.getSettingBool("group{}_enabled".format(self.kgroupID))

        self.transitionTime = int(
            ADDON.getSettingInt("group{}_TransitionTime".format(self.kgroupID)) / 100)  # This is given as a multiple of 100ms and defaults to 4 (400ms). For example, setting transitiontime:10 will make the transition last 1 second.
        self.forceOn = ADDON.getSettingBool("group{}_forceOn".format(self.kgroupID))
        self.disableLabs = ADDON.getSettingBool("group{}_disableLabs".format(self.kgroupID))
        self.minBri = ADDON.getSettingInt("group{}_MinBrightness".format(self.kgroupID)) * 255 / 100  # convert percentage to value 1-254
        self.maxBri = ADDON.getSettingInt("group{}_MaxBrightness".format(self.kgroupID)) * 255 / 100  # convert percentage to value 1-254
        self.saturation = ADDON.getSettingNumber("group{}_Saturation".format(self.kgroupID))
        self.captureSize = ADDON.getSettingInt("group{}_CaptureSize".format(self.kgroupID))
        self.resume_state = ADDON.getSettingBool("group{}_ResumeState".format(self.kgroupID))
        self.resume_transition = ADDON.getSettingInt("group{}_ResumeTransition".format(self.kgroupID)) * 10  # convert seconds to multiple of 100ms

        self.updateInterval = ADDON.getSettingInt("group{}_Interval".format(self.kgroupID)) / 1000  # convert MS to seconds
        if self.updateInterval == 0:
            self.updateInterval = 0.002

        self.ambiLights = {}
        lightIDs = ADDON.getSetting("group{}_Lights".format(self.kgroupID)).split(",")
        index = 0
        for L in lightIDs:
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
                reporting.process_exception(exc.type_id, exc.message)

    def onAVStarted(self):

        xbmc.log(
            "Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.playbackType(): {}".format(
                self.enabled, self.isPlayingVideo(), self.isPlayingAudio(), self.playback_type()))
        xbmc.log(
            "Ambilight Settings: Interval: {}, transitionTime: {}".format(self.updateInterval, self.transitionTime))

        self.state = STATE_PLAYING

        # save light state
        self.savedLightStates = kodihue._get_light_states(self.ambiLights, self.bridge)

        self.videoInfoTag = self.getVideoInfoTag()
        if self.isPlayingVideo():
            if self.enabled and self.check_active_time() and self.check_video_activation(self.videoInfoTag):

                if self.disableLabs:
                    self._stop_effects()

                if self.forceOn:
                    self._force_on(self.ambiLights, self.bridge, self.savedLightStates)

                self.ambiRunning.set()
                ambiLoopThread = Thread(target=self._ambi_loop, name="_ambiLoop")
                ambiLoopThread.daemon = True
                ambiLoopThread.start()

    def onPlayBackStopped(self):
        xbmc.log("[script.service.hue] In ambiGroup[{}], onPlaybackStopped()".format(self.kgroupID))
        self.state = STATE_STOPPED
        self.ambiRunning.clear()

        if self.disableLabs:
            self._resume_effects()

        if self.resume_state:
            self._resume_light_state()

    def onPlayBackPaused(self):
        xbmc.log("[script.service.hue] In ambiGroup[{}], onPlaybackPaused()".format(self.kgroupID))
        self.state = STATE_PAUSED
        self.ambiRunning.clear()

        if self.disableLabs:
            self._resume_effects()

        if self.resume_state:
            self._resume_light_state()

    def _resume_light_state(self):
        xbmc.log("[script.service.hue] Resuming light state")
        for L in self.savedLightStates:
            xy = self.savedLightStates[L]['state']['xy']
            bri = self.savedLightStates[L]['state']['bri']
            on = self.savedLightStates[L]['state']['on']
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
        service_enabled = cache.get("script.service.hue.service_enabled")
        aspect_ratio = cap.getAspectRatio()

        self.captureSizeY = int(self.captureSize / aspect_ratio)
        expected_capture_size = self.captureSize * self.captureSizeY * 4  # size * 4 bytes I guess
        xbmc.log(
            "aspect_ratio: {}, Capture Size: ({},{}), expected_capture_size: {}".format(aspect_ratio, self.captureSize,
                                                                                        self.captureSizeY,
                                                                                        expected_capture_size))

        for L in list(self.ambiLights):
            self.ambiLights[L].update(prevxy=(0.0001, 0.0001))

        try:
            while not self.monitor.abortRequested() and self.ambiRunning.is_set():  # loop until kodi tells add-on to stop or video playing flag is unset.
                try:
                    cap.capture(self.captureSize, self.captureSizeY)  # async capture request to underlying OS
                    capImage = cap.getImage()  # timeout to wait for OS in ms, default 1000

                    if capImage is None or len(capImage) < expected_capture_size:
                        # xbmc.log("[script.service.hue] capImage is none or < expected. captured: {}, expected: {}".format(len(capImage), expected_capture_size))
                        xbmc.sleep(250)  # pause before trying again
                        continue  # no image captured, try again next iteration
                    image = Image.frombytes("RGBA", (self.captureSize, self.captureSizeY), bytes(capImage), "raw", "BGRA", 0, 1)

                except ValueError:
                    xbmc.log("[script.service.hue] capImage: {}".format(len(capImage)))
                    xbmc.log("[script.service.hue] Value Error")
                    self.monitor.waitForAbort(0.25)
                    continue  # returned capture is  smaller than expected when player stopping. give up this loop.
                except Exception as exc:
                    xbmc.log("[script.service.hue] Capture exception", exc_info=1)
                    reporting.process_exception(exc)
                    self.monitor.waitForAbort(0.25)
                    continue

                colors = self.imageProcess.img_avg(image, self.minBri, self.maxBri, self.saturation)
                for L in list(self.ambiLights):
                    x = Thread(target=self._update_hue_rgb, name="updateHue", args=(
                        colors['rgb'][0], colors['rgb'][1], colors['rgb'][2], L, self.transitionTime, colors['bri']))
                    x.daemon = True
                    x.start()

                if not cache.get("script.service.hue.service_enabled"):
                    xbmc.log("[script.service.hue] Service disabled, stopping Ambilight")
                    self.ambiRunning.clear()
                self.monitor.waitForAbort(self.updateInterval)  # seconds

            average_process_time = kodihue._perf_average(PROCESS_TIMES)
            xbmc.log("[script.service.hue] Average process time: {}".format(average_process_time))
            self.captureSize = ADDON.setSetting("average_process_time", str(average_process_time))

        except Exception as exc:
            xbmc.log("[script.service.hue] Exception in _ambiLoop")
            reporting.process_exception(exc)
        xbmc.log("[script.service.hue] _ambiLoop stopped")

    def _update_hue_rgb(self, r, g, b, light, transitionTime, bri):
        gamut = self.ambiLights[light].get('gamut')
        prevxy = self.ambiLights[light].get('prevxy')

        if gamut == "A":
            converter = self.converterA
        elif gamut == "B":
            converter = self.converterB
        elif gamut == "C":
            converter = self.converterC

        xy = converter.rgb_to_xy(r, g, b)
        xy = round(xy[0], 3), round(xy[1], 3)  # Hue has a max precision of 4 decimal points, but three is enough
        distance = self.helper.get_distance_between_two_points(XYPoint(xy[0], xy[1]), XYPoint(prevxy[0], prevxy[1]))  # only update hue if XY changed enough

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

        self.bridgeError500 = self.bridgeError500 + 1  # increment counter
        if self.bridgeError500 > 100 and settings_storage['show500Error']:
            stopShowingError = xbmcgui.Dialog().yesno(_("Hue Bridge over capacity"), _("The Hue Bridge is over capacity. Increase refresh rate or reduce the number of Ambilights."), yeslabel=_("Do not show again"), nolabel=_("Ok"))

            if stopShowingError:
                ADDON.setSettingBool("show500Error", False)
            self.bridgeError500 = 0

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
        allSensors = self.bridge.sensors()
        effects = [id
                   for id, sensor in list(allSensors.items())
                   if sensor['modelid'] == 'HUELABSVTOGGLE' and 'status' in sensor['state'] and sensor['state']['status'] == 1
                   ]

        # For each effect, find the linked lights or groups
        allLinks = self.bridge.resourcelinks()
        for sensor in effects:
            sensorLinks = [sensorLink
                           for link in list(allLinks.values())
                           for sensorLink in link['links']
                           if '/sensors/' + sensor in link['links']
                           ]

            for link in sensorLinks:
                i = link.split('/')[-1]
                if link.startswith('/lights/'):
                    lights.setdefault(i, set())
                    lights[i].add(sensor)
                elif link.startswith('/groups/'):
                    groups.setdefault(i, set())
                    groups[i].add(sensor)

        # For linked groups, find their associated lights
        allGroups = self.bridge.groups()
        for g, sensors in list(groups.items()):
            for i in allGroups[g]['lights']:
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
                    and i in self.savedLightStates
                    and self.savedLightStates[i]['state']['on']
                    for sensor in lights[i]
                    ])
