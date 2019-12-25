# -*- coding: utf-8 -*-
from threading import Thread, Event


import xbmc
from PIL import Image

from resources.lib import kodiHue, PROCESS_TIMES, cache, reporting

from . import ImageProcess
from . import KodiGroup
from . import MINIMUM_COLOR_DISTANCE
from . import ADDON, logger
from .KodiGroup import VIDEO, STATE_STOPPED, STATE_PAUSED, STATE_PLAYING
from .qhue import QhueException
from .rgbxy import Converter, ColorHelper  # https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA, GamutB, GamutC


class AmbiGroup(KodiGroup.KodiGroup):
    def __init__(self):
        super(AmbiGroup, self).__init__()

    def onAVStarted(self):
        logger.info(
            "Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(
                self.enabled, self.isPlayingVideo(), self.isPlayingAudio(), self.mediaType, self.playbackType()))
        logger.info(
            "Ambilight Settings: Interval: {}, transitionTime: {}".format(self.updateInterval, self.transitionTime))

        self.state = STATE_PLAYING

        # save light state
        self.savedLightStates = kodiHue.get_light_states(self.ambiLights, self.bridge)

        self.videoInfoTag = self.getVideoInfoTag()
        if self.isPlayingVideo():
            if self.enabled and self.checkActiveTime() and self.checkVideoActivation(self.videoInfoTag):

                if self.forceOn:
                    for L in self.ambiLights:
                        try:
                            self.bridge.lights[L].state(on=True)
                        except QhueException as e:
                            logger.debug("Ambi: Initial Hue call fail: {}".format(e))
                            reporting.process_exception(e)

                self.ambiRunning.set()
                ambiLoopThread = Thread(target=self._ambiLoop, name="_ambiLoop")
                ambiLoopThread.daemon = True
                ambiLoopThread.start()


    def onPlayBackStopped(self):
        logger.info("In ambiGroup[{}], onPlaybackStopped()".format(self.kgroupID))
        self.state = STATE_STOPPED
        self.ambiRunning.clear()

        if self.resume_state:
            self.resumeLightState()


    def onPlayBackPaused(self):
        logger.info("In ambiGroup[{}], onPlaybackPaused()".format(self.kgroupID))
        self.state = STATE_PAUSED
        self.ambiRunning.clear()
        if self.resume_state:
            self.resumeLightState()


    def resumeLightState(self):
        logger.info("Resuming light state")
        for L in self.savedLightStates:
            xy = self.savedLightStates[L]['state']['xy']
            bri = self.savedLightStates[L]['state']['bri']
            on = self.savedLightStates[L]['state']['on']
            logger.debug("Resume state: Light: {}, xy: {}, bri: {}, on: {},transition time: {}".format(L, xy, bri, on, self.resume_transition))
            try:
                self.bridge.lights[L].state(xy=xy, bri=bri, on=on, transitiontime=self.resume_transition)
            except QhueException as exc:
                logger.error("onPlaybackStopped: Hue call fail: {}".format(exc))
                reporting.process_error(exc)


    def loadSettings(self):
        logger.debug("AmbiGroup Load settings")

        self.enabled = ADDON.getSettingBool("group{}_enabled".format(self.kgroupID))

        self.transitionTime = ADDON.getSettingInt("group{}_TransitionTime".format(self.kgroupID)) / 100  # This is given as a multiple of 100ms and defaults to 4 (400ms). For example, setting transitiontime:10 will make the transition last 1 second.
        self.forceOn = ADDON.getSettingBool("group{}_forceOn".format(self.kgroupID))

        self.minBri = ADDON.getSettingInt("group{}_MinBrightness".format(self.kgroupID)) * 255 / 100  # convert percentage to value 1-254
        self.maxBri = ADDON.getSettingInt("group{}_MaxBrightness".format(self.kgroupID)) * 255 / 100  # convert percentage to value 1-254

        self.saturation = ADDON.getSettingNumber("group{}_Saturation".format(self.kgroupID))
        self.captureSize = ADDON.getSettingInt("group{}_CaptureSize".format(self.kgroupID))

        self.resume_state = ADDON.getSettingBool("group{}_ResumeState".format(self.kgroupID))
        self.resume_transition = ADDON.getSettingInt("group{}_ResumeTransition".format(self.kgroupID)) * 10 #convert seconds to multiple of 100ms

        self.updateInterval = ADDON.getSettingInt("group{}_Interval".format(self.kgroupID)) / 1000  # convert MS to seconds
        if self.updateInterval == 0:
            self.updateInterval = 0.002

        self.ambiLights = {}
        lightIDs = ADDON.getSetting("group{}_Lights".format(self.kgroupID)).split(",")
        index = 0
        for L in lightIDs:
            gamut = kodiHue.getLightGamut(self.bridge, L)
            light = {L: {'gamut': gamut, 'prevxy': (0, 0), "index": index}}
            self.ambiLights.update(light)
            index = index + 1

    def setup(self, monitor, bridge, kgroupID, flash=False):
        try:
            self.ambiRunning
        except AttributeError:
            self.ambiRunning = Event()

        super(AmbiGroup, self).setup(bridge, kgroupID, flash, VIDEO)
        self.monitor = monitor

        self.imageProcess = ImageProcess.ImageProcess()

        self.converterA = Converter(GamutA)
        self.converterB = Converter(GamutB)
        self.converterC = Converter(GamutC)
        self.helper = ColorHelper(GamutC)

    def _ambiLoop(self):

        cap = xbmc.RenderCapture()
        logger.debug("_ambiLoop started")
        service_enabled = cache.get("script.service.hue.service_enabled")
        aspect_ratio = cap.getAspectRatio()

        self.captureSizeY = int(self.captureSize / aspect_ratio)
        expected_capture_size = self.captureSize * self.captureSizeY * 4  # size * 4 bytes I guess
        logger.debug(
            "aspect_ratio: {}, Capture Size: ({},{}), expected_capture_size: {}".format(aspect_ratio, self.captureSize,
                                                                                        self.captureSizeY,
                                                                                        expected_capture_size))

        for L in self.ambiLights:
            self.ambiLights[L].update(prevxy=(0.0001, 0.0001))

        try:
            while not self.monitor.abortRequested() and self.ambiRunning.is_set():  # loop until kodi tells add-on to stop or video playing flag is unset.
                try:
                    cap.capture(self.captureSize, self.captureSizeY)  # async capture request to underlying OS
                    capImage = cap.getImage()  # timeout to wait for OS in ms, default 1000
                    # logger.debug("CapSize: {}".format(len(capImage)))
                    if capImage is None or len(capImage) < expected_capture_size:
                        logger.error("capImage is none or < expected. captured: {}, expected: {}".format(len(capImage),
                                                                                                         expected_capture_size))
                        self.monitor.waitForAbort(0.25)  # pause before trying again
                        continue  # no image captured, try again next iteration
                    image = Image.frombuffer("RGBA", (self.captureSize, self.captureSizeY), buffer(capImage), "raw",
                                             "BGRA")
                except ValueError:
                    logger.error("capImage: {}".format(len(capImage)))
                    logger.exception("Value Error")
                    self.monitor.waitForAbort(0.25)
                    continue  # returned capture is  smaller than expected when player stopping. give up this loop.
                except Exception as exc:
                    logger.warning("Capture exception", exc_info=1)
                    reporting.process_exception(exc)
                    self.monitor.waitForAbort(0.25)
                    continue

                colors = self.imageProcess.img_avg(image, self.minBri, self.maxBri, self.saturation)
                for L in self.ambiLights:
                    x = Thread(target=self._updateHueRGB, name="updateHue", args=(
                        colors['rgb'][0], colors['rgb'][1], colors['rgb'][2], L, self.transitionTime, colors['bri']))
                    x.daemon = True
                    x.start()

                if not cache.get("script.service.hue.service_enabled"):
                    logger.info("Service disabled, stopping Ambilight")
                    self.ambiRunning.clear()
                self.monitor.waitForAbort(self.updateInterval)  # seconds

            average_process_time = kodiHue.perfAverage(PROCESS_TIMES)
            logger.info("Average process time: {}".format(average_process_time))
            self.captureSize = ADDON.setSettingString("average_process_time", "{}".format(average_process_time))

        except Exception as exc:
            logger.exception("Exception in _ambiLoop")
            reporting.process_exception(exc)
        logger.debug("_ambiLoop stopped")

    def _updateHueRGB(self, r, g, b, light, transitionTime, bri):
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
        distance = self.helper.get_distance_between_two_points(XYPoint(xy[0], xy[1]), XYPoint(prevxy[0], prevxy[
            1]))  # only update hue if XY changed enough

        if distance > MINIMUM_COLOR_DISTANCE:
            # if xy != prevxy:  # only update if value changed
            try:
                self.bridge.lights[light].state(xy=xy, bri=bri, transitiontime=transitionTime)
                self.ambiLights[light].update(prevxy=xy)
            except QhueException as exc:
                if exc.args[0][0] == 201:  # Param not modifiable because light is off error. ignore
                    pass
                else:
                    logger.exception("Ambi: Hue call fail: {}".format(exc))
                    reporting.process_exception(exc)

            except KeyError:
                logger.exception("Ambi: KeyError")

    def _updateHueXY(self, xy, light, transitionTime):

        prevxy = self.ambiLights[light].get('prevxy')

        # xy=(round(xy[0],3),round(xy[1],3)) #Hue has a max precision of 4 decimal points.

        # distance=self.helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1]))#only update hue if XY changed enough
        # if distance > self.minimumDistance:
        try:
            self.bridge.lights[light].state(xy=xy, transitiontime=transitionTime)
            self.ambiLights[light].update(prevxy=xy)
        except QhueException as exc:
            if exc.args[0] == 201: # Param not modifiable because light is off error. ignore
                pass
            else:
                logger.exception("Ambi: Hue call fail: {}".format(exc.args))
                reporting.process_exception(exc)

        except KeyError:
            logger.exception("Ambi: KeyError")
