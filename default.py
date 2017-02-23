from threading import Timer
import colorsys
import json
import math
import os
import sys
import time

import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__cwd__ = __addon__.getAddonInfo('path')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))

sys.path.append(__resource__)

from settings import settings
from tools import notify, ChapterManager, Logger, get_version
import bridge
import lights
import image

xbmc.log("Kodi Hue service started, version: %s" % get_version())

capture = xbmc.RenderCapture()
fmt = capture.getImageFormat()
# BGRA or RGBA
fmtRGBA = fmt == 'RGBA'


class RepeatedTimer(object):

    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class MyMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        logger.debuglog("running in mode %s" % str(hue.settings.mode))
        hue.settings.readxml()
        hue.update_settings()


class MyPlayer(xbmc.Player):
    duration = 0
    playingvideo = False
    playlistlen = 0
    timer = None
    movie = False

    def __init__(self):
        xbmc.Player.__init__(self)

    def checkTime(self):
        if self.isPlayingVideo():
            check_time(int(self.getTime()))  # call back out to plugin function.

    def onPlayBackStarted(self):
        xbmc.log("Kodi Hue: DEBUG playback started called on player")
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playlistlen = playlist.size()
        self.playlistpos = playlist.getposition()

        if self.isPlayingVideo() and not self.playingvideo:
            self.playingvideo = True
            self.duration = self.getTotalTime()
            self.movie = xbmc.getCondVisibility('VideoPlayer.Content(movies)')

            global credits_triggered
            credits_triggered = False
            if self.movie and self.duration != 0:  # only try if its a movie and has a duration
                # TODO: start it on a timer to not block the beginning of the
                # media
                get_credits_info(
                    self.getVideoInfoTag().getTitle(),
                    self.duration)
                logger.debuglog("credits_time: %r" % credits_time)
                self.timer = RepeatedTimer(1, self.checkTime)
            state_changed("started", self.duration)

    def onPlayBackPaused(self):
        xbmc.log("Kodi Hue: DEBUG playback paused called on player")
        if self.isPlayingVideo():
            self.playingvideo = False
            if self.movie and not self.timer is None:
                self.timer.stop()
            state_changed("paused", self.duration)

    def onPlayBackResumed(self):
        logger.debuglog("playback resumed called on player")
        if self.isPlayingVideo():
            self.playingvideo = True
            if self.duration == 0:
                self.duration = self.getTotalTime()
                if self.movie and self.duration != 0:  # only try if its a movie and has a duration
                    # TODO: start it on a timer to not block the beginning of
                    # the media
                    get_credits_info(
                        self.getVideoInfoTag().getTitle(), self.duration)
                    logger.debuglog("credits_time: %r" % credits_time)
            if self.movie and self.duration != 0:
                self.timer = RepeatedTimer(1, self.checkTime)
            state_changed("resumed", self.duration)

    def onPlayBackStopped(self):
        xbmc.log("Kodi Hue: DEBUG playback stopped called on player")
        self.playingvideo = False
        self.playlistlen = 0
        if self.movie and not self.timer is None:
            self.timer.stop()
        state_changed("stopped", self.duration)

    def onPlayBackEnded(self):
        xbmc.log("Kodi Hue: DEBUG playback ended called on player")
        # If there are upcoming plays, ignore
        if self.playlistpos < self.playlistlen-1:
            return

        self.playingvideo = False
        if self.movie and not self.timer is None:
            self.timer.stop()
        state_changed("stopped", self.duration)


class Hue:
    params = None
    connected = None
    last_state = None
    light = None
    ambilight_dim_light = None
    pauseafterrefreshchange = 0

    def __init__(self, settings, args):
        # Logs are good, mkay.
        self.logger = Logger()
        if settings.debug:
            self.logger.debug()

        # get settings
        self.settings = settings
        self._parse_argv(args)

        # if there's a bridge user, lets instantiate the lights (only if we're
        # connected).
        if self.settings.bridge_user not in ["-", "", None] and self.connected:
            self.update_settings()

        if self.params == {}:
            self.logger.debuglog("params: %s" % self.params)
            # if there's a bridge IP, try to talk to it.
            if self.settings.bridge_ip not in ["-", "", None]:
                result = self.test_connection()
                if result:
                    self.update_settings()
        elif self.params['action'] == "discover":
            self.logger.debuglog("Starting discovery")
            notify("Bridge Discovery", "starting")
            hue_ip = self.start_autodiscover()
            if hue_ip is not None:
                notify("Bridge Discovery", "Found bridge at: %s" % hue_ip)
                username = self.register_user(hue_ip)
                self.logger.debuglog("Updating settings")
                self.settings.update(bridge_ip=hue_ip)
                self.settings.update(bridge_user=username)
                notify("Bridge Discovery", "Finished")
                self.test_connection()
                self.update_settings()
            else:
                notify("Bridge Discovery", "Failed. Could not find bridge.")
        elif self.params['action'] == "reset_settings":
            self.logger.debuglog("Reset Settings to default.")
            self.logger.debuglog(__addondir__)
            os.unlink(os.path.join(__addondir__, "settings.xml"))
        else:
            # not yet implemented
            self.logger.debuglog(
                "unimplemented action call: %s" %
                self.params['action'])

        # detect pause for refresh change (must reboot for this to take effect.)
        response = json.loads(
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Settings.GetSettingValue", "params":{"setting":"videoscreen.delayrefreshchange"},"id":1}'))
        if "result" in response and "value" in response["result"]:
            pauseafterrefreshchange = int(response["result"]["value"])

        if self.connected:
            if self.settings.misc_initialflash:
                self.flash_lights()

    def start_autodiscover(self):
        return bridge.discover()

    def register_user(self, hue_ip):
        return bridge.create_user(hue_ip)

    def flash_lights(self):
        self.logger.debuglog("class Hue: flashing lights")
        self.light.flash_lights()

    def _parse_argv(self, args):
        try:
            self.params = dict(arg.split("=") for arg in args.split("&"))
        except:
            self.params = {}

    def test_connection(self):
        self.connected = bridge.user_exists(self.settings.bridge_ip,
                                            self.settings.bridge_user)
        return self.connected

    def dim_lights(self):
        self.logger.debuglog("class Hue: dim lights")
        self.last_state = "dimmed"
        self.light.dim_lights()

    def brighter_lights(self):
        self.logger.debuglog("class Hue: brighter lights")
        self.last_state = "brighter"
        self.light.brighter_lights()

    def partial_lights(self):
        self.logger.debuglog("class Hue: partial lights")
        self.last_state = "partial"
        self.light.partial_lights()

    def update_settings(self):
        self.logger.debuglog("class Hue: update settings")
        self.logger.debuglog(settings)
        if self.settings.light == 0:
            available = bridge.get_lights_by_group(self.settings.bridge_ip,
                                                   self.settings.bridge_user,
                                                   self.settings.group_id)
            self.light = lights.Controller(available, self.settings)
        elif self.settings.light > 0:
            light_ids = [self.settings.light1_id]
            if self.settings.light > 1:
                light_ids.append(self.settings.light2_id)
            if self.settings.light > 2:
                light_ids.append(self.settings.light3_id)
                available = bridge.get_lights_by_ids(self.settings.bridge_ip,
                                                     self.settings.bridge_user,
                                                     light_ids)
                self.light = lights.Controller(available, self.settings)
        # ambilight dim
        if self.settings.ambilight_dim:
            if self.settings.ambilight_dim_light == 0:
                available = bridge.get_lights_by_group(
                    self.settings.bridge_ip, self.settings.bridge_user,
                    self.settings.ambilight_dim_group_id)
                self.ambilight_dim_light = lights.Controller(available,
                                                             self.settings)
            elif self.settings.ambilight_dim_light > 0:
                light_ids = [self.settings.ambilight_dim_light1_id]
                if self.settings.ambilight_dim_light > 1:
                    light_ids.append(self.settings.ambilight_dim_light2_id)
                if self.settings.ambilight_dim_light > 2:
                    light_ids.append(self.settings.ambilight_dim_light3_id)
                available = bridge.get_lights_by_ids(self.settings.bridge_ip,
                                                     self.settings.bridge_user,
                                                     light_ids)
                self.ambilight_dim_light = lights.Controller(available,
                                                             self.settings)


def run():
    player = MyPlayer()
    if player is None:
        logger.log("Cannot instantiate player. Bailing out")
        return
    last = time.time()

    while not monitor.abortRequested():
        if hue.settings.mode == 0:  # ambilight mode
            now = time.time()
            last = now

            startReadOut = False
            vals = {}
            # live tv does not trigger playbackstart
            if player.isPlayingVideo() and not player.playingvideo:
                player.playingvideo = True
                state_changed("started", player.getTotalTime())
                continue
            if player.playingvideo:  # only if there's actually video
                try:
                    vals = capture.getImage(200)
                    if len(vals) > 0 and player.playingvideo:
                        startReadOut = True
                    if startReadOut:
                        screen = image.Screenshot(
                            capture.getImage())
                        hsvRatios = screen.spectrum_hsv(
                            screen.pixels,
                            hue.settings.ambilight_threshold_value,
                            hue.settings.ambilight_threshold_saturation,
                            hue.settings.color_bias
                        )
                        xbmc.log("Kodi Hue: DEBUG hsvratios {}".format(hsvRatios))
                        if hue.settings.light == 0:
                            fade_light_hsv(hue.light.lights[0], hsvRatios[0])
                        else:
                            for i in range(hue.settings.light):
                                fade_light_hsv(hue.light.lights[i], hsvRatios[i])
                except ZeroDivisionError:
                    logger.debuglog("no frame. looping.")

        if monitor.waitForAbort(0.1):
            # kodi requested an abort, lets get out of here.
            break

    del player  # might help with slow exit.


def fade_light_hsv(light, hsvRatio):
    fullspectrum = light.fullspectrum
    h, s, v = hsvRatio.hue(
        fullspectrum, hue.settings.ambilight_min, hue.settings.ambilight_max
    )
    hvec = abs(h - light.last_hue) % int(65535/2)
    hvec = float(hvec/128.0)
    svec = s - light.last_sat
    vvec = v - light.last_bri
    # changed to squares for performance
    distance = math.sqrt(hvec**2 + svec**2 + vvec**2)
    if distance > 0:
        duration = int(10 - 2.5 * distance/255)
        light.set_state(hue=h, sat=s, bri=v, transition_time=duration)

credits_time = None  # test = 10
credits_triggered = False


def get_credits_info(title, duration):
    logger.debuglog("get_credits_info")
    if hue.settings.undim_during_credits:
        # get credits time here
        logger.debuglog("title: %r, duration: %r" % (title, duration))
        global credits_time
        credits_time = ChapterManager.CreditsStartTimeForMovie(title, duration)
        logger.debuglog("set credits time to: %r" % credits_time)


def check_time(cur_time):
    global credits_triggered
    if hue.settings.undim_during_credits and credits_time is not None:
        if (cur_time >= credits_time +
                hue.settings.credits_delay_time) and not credits_triggered:
            logger.debuglog("hit credits, turn on lights")
            # do partial undim (if enabled, otherwise full undim)
            if hue.settings.mode == 0 and hue.settings.ambilight_dim:
                hue.ambilight_dim_light.brighter_lights()
            else:
                hue.brighter_lights()
            credits_triggered = True
        elif (cur_time < credits_time + hue.settings.credits_delay_time) and credits_triggered:
            # still before credits, if this has happened, we've rewound
            credits_triggered = False


def state_changed(state, duration):
    logger.debuglog("state changed to: %s" % state)

    if (xbmc.getCondVisibility('Window.IsActive(screensaver-atv4.xml)') or
        xbmc.getCondVisibility('Window.IsActive(screensaver-video-main.xml)')):
        logger.debuglog("add-on disabled for screensavers")
        return

    if duration < hue.settings.misc_disableshort_threshold and hue.settings.misc_disableshort:
        logger.debuglog("add-on disabled for short movies")
        return

    if state == "started":
        logger.debuglog("retrieving current setting before starting")

        # start capture when playback starts
        capture_width = 32  # 100
        capture_height = capture_width / capture.getAspectRatio()
        if capture_height == 0:
            capture_height = capture_width  # fix for divide by zero.
        logger.debuglog("capture %s x %s" % (capture_width, capture_height))
        capture.capture(int(capture_width), int(capture_height))

    if (state == "started" and hue.pauseafterrefreshchange == 0) or state == "resumed":
        if hue.settings.ambilight_dim:  # if in ambilight mode and dimming is enabled
            if hue.settings.ambilight_dim_light >= 0:
                hue.ambilight_dim_light.dim_lights()
        else:
            hue.dim_lights()
    elif state == "paused" and hue.last_state == "dimmed":
        if hue.settings.ambilight_dim:
            if hue.settings.ambilight_dim_light >= 0:
                hue.ambilight_dim_light.partial_lights()
        else:
            hue.partial_lights()
    elif state == "stopped":
        if hue.settings.ambilight_dim:
            if hue.settings.ambilight_dim_light >= 0:
                hue.ambilight_dim_light.undim_lights()
        else:
            hue.undim_lights()

if (__name__ == "__main__"):
    settings = settings()
    logger = Logger()
    monitor = MyMonitor()
    if settings.debug:
        logger.debug()

    args = None
    if len(sys.argv) == 2:
        args = sys.argv[1]
    hue = Hue(settings, args)
    while not hue.connected and not monitor.abortRequested():
        logger.debuglog("not connected")
        time.sleep(1)
    run()
