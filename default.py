from threading import Timer
import colorsys
import datetime
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
from tools import notify, Light, Group, ChapterManager, Logger, get_version

try:
    import requests
except ImportError:
    xbmc.log("ERROR: Could not locate required library requests")
    notify("Kodi Hue", "ERROR: Could not import Python requests")

xbmc.log("Kodi Hue service started, version: %s" % get_version())

capture = xbmc.RenderCapture()
useLegacyApi = True
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
        last = datetime.datetime.now()
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
        port = 1900
        ip = "239.255.255.250"

        address = (ip, port)
        data = """M-SEARCH * HTTP/1.1
    HOST: %s:%s
    MAN: ssdp:discover
    MX: 3
    ST: upnp:rootdevice
    """ % (ip, port)
        client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP)  # force udp
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        hue_ip = None
        num_retransmits = 0
        while(num_retransmits < 10) and hue_ip is None:
            num_retransmits += 1
            try:
                client_socket.sendto(data, address)
                recv_data, addr = client_socket.recvfrom(2048)
                self.logger.debuglog(
                    "received data during autodiscovery: "+recv_data)
                if "IpBridge" in recv_data and "description.xml" in recv_data:
                    hue_ip = recv_data.split(
                        "LOCATION: http://")[1].split(":")[0]
                time.sleep(1)
            except socket.timeout:
                # if the socket times out once, its probably not going to
                # complete at all. fallback to nupnp.
                break

        if hue_ip is None:
            # still nothing found, try alternate api
            # verify false hack until meethue fixes their ssl cert.
            r = requests.get("https://www.meethue.com/api/nupnp", verify=False)
            j = r.json()
            if len(j) > 0:
                hue_ip = j[0]["internalipaddress"]
                self.logger.debuglog("meethue nupnp api returned: "+hue_ip)
            else:
                self.logger.debuglog("meethue nupnp api did not find bridge")

        return hue_ip

    def register_user(self, hue_ip):
        device = "kodi#ambilight"
        data = '{"devicetype": "%s"}' % device
        self.logger.debuglog("sending data: %s" % data)

        r = requests.post('http://%s/api' % hue_ip, data=data)
        response = r.text
        while "link button not pressed" in response:
            self.logger.debuglog("register user response: %s" % r)
            notify("Bridge Discovery", "Press link button on bridge")
            r = requests.post('http://%s/api' % hue_ip, data=data)
            response = r.text
            time.sleep(3)

        j = r.json()
        self.logger.debuglog("got a username response: %s" % j)
        username = j[0]["success"]["username"]

        return username

    def flash_lights(self):
        self.logger.debuglog("class Hue: flashing lights")
        if self.settings.light == 0:
            self.light.flash_light()
        else:
            self.light[0].flash_light()
            if self.settings.light > 1:
                xbmc.sleep(1)
                self.light[1].flash_light()
            if self.settings.light > 2:
                xbmc.sleep(1)
                self.light[2].flash_light()

    def _parse_argv(self, args):
        try:
            self.params = dict(arg.split("=") for arg in args.split("&"))
        except:
            self.params = {}

    def test_connection(self):
        self.logger.debuglog("testing connection")
        r = requests.get('http://%s/api/%s/config' %
                         (self.settings.bridge_ip, self.settings.bridge_user))
        test_connection = r.text.find("name")
        if not test_connection:
            notify("Failed", "Could not connect to bridge")
            self.connected = False
        else:
            notify("Kodi Hue", "Connected")
            self.connected = True
        return self.connected

    def dim_lights(self):
        self.logger.debuglog("class Hue: dim lights")
        self.last_state = "dimmed"
        if self.settings.light == 0:
            self.light.dim_light()
        else:
            self.light[0].dim_light()
            if self.settings.light > 1:
                xbmc.sleep(1)
                self.light[1].dim_light()
            if self.settings.light > 2:
                xbmc.sleep(1)
                self.light[2].dim_light()

    def brighter_lights(self):
        self.logger.debuglog("class Hue: brighter lights")
        self.last_state = "brighter"
        if self.settings.light == 0:
            self.light.brighter_light()
        else:
            self.light[0].brighter_light()
            if self.settings.light > 1:
                xbmc.sleep(1)
                self.light[1].brighter_light()
            if self.settings.light > 2:
                xbmc.sleep(1)
                self.light[2].brighter_light()

    def partial_lights(self):
        self.logger.debuglog("class Hue: partial lights")
        self.last_state = "partial"
        if self.settings.light == 0:
            self.light.partial_light()
        else:
            self.light[0].partial_light()
            if self.settings.light > 1:
                xbmc.sleep(1)
                self.light[1].partial_light()
            if self.settings.light > 2:
                xbmc.sleep(1)
                self.light[2].partial_light()

    def update_settings(self):
        self.logger.debuglog("class Hue: update settings")
        self.logger.debuglog(settings)
        if self.settings.light == 0 and \
                (self.light is None or not isinstance(self.light, Group)):
            self.logger.debuglog("creating Group instance")
            self.light = Group(self.settings)
        elif self.settings.light > 0 and \
            (self.light is None or
             isinstance(self.light, Group) or
             len(self.light) != self.settings.light or
             self.light[0].light != self.settings.light1_id or
             (self.settings.light > 1 and self.light[1].light != self.settings.light2_id) or
             (self.settings.light > 2 and self.light[2].light != self.settings.light3_id)):
            self.logger.debuglog("creating Light instances")
            self.light = [None] * self.settings.light
            self.light[0] = Light(self.settings.light1_id, self.settings)
            if self.settings.light > 1:
                xbmc.sleep(1)
                self.light[1] = Light(self.settings.light2_id, self.settings)
            if self.settings.light > 2:
                xbmc.sleep(1)
                self.light[2] = Light(self.settings.light3_id, self.settings)
        # ambilight dim
        if self.settings.ambilight_dim:
            if self.settings.ambilight_dim_light == 0 and (
                self.ambilight_dim_light is None or not isinstance(
                    self.ambilight_dim_light, Group)):
                self.logger.debuglog(
                    "creating Group instance for ambilight dim")
                self.ambilight_dim_light = Group(
                    self.settings, self.settings.ambilight_dim_group_id)
            elif self.settings.ambilight_dim_light > 0 and \
                (self.ambilight_dim_light is None or
                 isinstance(self.ambilight_dim_light, Group) or
                 len(self.ambilight_dim_light) != self.settings.ambilight_dim_light or
                 self.ambilight_dim_light[0].light != self.settings.ambilight_dim_light1_id or
                 (self.settings.ambilight_dim_light > 1 and self.ambilight_dim_light[1].light != self.settings.ambilight_dim_light2_id) or
                 (self.settings.ambilight_dim_light > 2 and self.ambilight_dim_light[2].light != self.settings.ambilight_dim_light3_id)):
                self.logger.debuglog(
                    "creating Light instances for ambilight dim")
                self.ambilight_dim_light = [
                    None] * self.settings.ambilight_dim_light
                self.ambilight_dim_light[0] = Light(
                    self.settings.ambilight_dim_light1_id, self.settings)
                if self.settings.ambilight_dim_light > 1:
                    xbmc.sleep(1)
                    self.ambilight_dim_light[1] = Light(
                        self.settings.ambilight_dim_light2_id, self.settings)
                if self.settings.ambilight_dim_light > 2:
                    xbmc.sleep(1)
                    self.ambilight_dim_light[2] = Light(
                        self.settings.ambilight_dim_light3_id, self.settings)


class HSVRatio:
    cyan_min = float(4.5/12.0)
    cyan_max = float(7.75/12.0)

    def __init__(self, hue=0.0, saturation=0.0, value=0.0, ratio=0.0):
        self.h = hue
        self.s = saturation
        self.v = value
        self.ratio = ratio

    def average(self, h, s, v):
        self.h = (self.h + h)/2
        self.s = (self.s + s)/2
        self.v = (self.v + v)/2

    def averageValue(self, overall_value):
        if self.ratio > 0.5:
            self.v = self.v * self.ratio + overall_value * (1-self.ratio)
        else:
            self.v = (self.v + overall_value)/2

    def hue(self, fullSpectrum):
        if not fullSpectrum:
            if self.h > 0.065 and self.h < 0.19:
                self.h = self.h * 2.32
            elif self.s > 0.01:
                if self.h < 0.5:
                    # yellow-green correction
                    self.h = self.h * 1.17
                    # cyan-green correction
                    if self.h > self.cyan_min:
                        self.h = self.cyan_min
                else:
                    # cyan-blue correction
                    if self.h < self.cyan_max:
                        self.h = self.cyan_max

        h = int(self.h*65535)  # on a scale from 0 <-> 65535
        s = int(self.s*255)
        v = int(self.v*255)
        if v < hue.settings.ambilight_min:
            v = hue.settings.ambilight_min
        if v > hue.settings.ambilight_max:
            v = hue.settings.ambilight_max
        return h, s, v

    def __repr__(self):
        return 'h: %s s: %s v: %s ratio: %s' % (
            self.h, self.s, self.v, self.ratio)


class Screenshot:

    def __init__(self, pixels, capture_width, capture_height):
        self.pixels = pixels
        self.capture_width = capture_width
        self.capture_height = capture_height

    def most_used_spectrum(
        self,
        spectrum,
        saturation,
        value,
        size,
     overall_value):
        # color bias/groups 6 - 36 in steps of 3
        colorGroups = settings.color_bias
        colorHueRatio = 360 / colorGroups

        hsvRatios = []
        hsvRatiosDict = {}

        for i in spectrum:
            # shift index to the right so that groups are centered on primary
            # and secondary colors
            colorIndex = int(((i+colorHueRatio/2) % 360)/colorHueRatio)
            pixelCount = spectrum[i]

            try:
                hsvr = hsvRatiosDict[colorIndex]
                hsvr.average(i/360.0, saturation[i], value[i])
                hsvr.ratio = hsvr.ratio + pixelCount / float(size)
            except KeyError:
                hsvr = HSVRatio(
                    i / 360.0, saturation[i],
                    value[i],
                    pixelCount / float(size))
                hsvRatiosDict[colorIndex] = hsvr
                hsvRatios.append(hsvr)

        colorCount = len(hsvRatios)
        if colorCount > 1:
            # sort colors by popularity
            hsvRatios = sorted(
                hsvRatios,
                key=lambda hsvratio: hsvratio.ratio,
                reverse=True)
            # logger.debuglog("hsvRatios %s" % hsvRatios)

            # return at least 3
            if colorCount == 2:
                hsvRatios.insert(0, hsvRatios[0])

            hsvRatios[0].averageValue(overall_value)
            hsvRatios[1].averageValue(overall_value)
            hsvRatios[2].averageValue(overall_value)
            return hsvRatios

        elif colorCount == 1:
            hsvRatios[0].averageValue(overall_value)
            return [hsvRatios[0]] * 3

        return [HSVRatio()] * 3

    def spectrum_hsv(self, pixels, width, height):
        spectrum = {}
        saturation = {}
        value = {}

        size = int(len(pixels)/4)

        v = 0
        r, g, b = 0, 0, 0
        tmph, tmps, tmpv = 0, 0, 0
        overall_value = 1

        for i in range(0, size, 4):
            r, g, b = _rgb_from_pixels(pixels, i)
            tmph, tmps, tmpv = colorsys.rgb_to_hsv(
                float(r/255.0), float(g/255.0), float(b/255.0))
            v += tmpv

            # skip low value and saturation
            if tmpv > hue.settings.ambilight_threshold_value:
                if tmps > hue.settings.ambilight_threshold_saturation:
                    h = int(tmph * 360)
                    try:
                        spectrum[h] += 1
                        saturation[h] = (saturation[h] + tmps)/2
                        value[h] = (value[h] + tmpv)/2
                    except KeyError:
                        spectrum[h] = 1
                        saturation[h] = tmps
                        value[h] = tmpv

        if size > 0:
            overall_value = v / float(len(pixels))

        return self.most_used_spectrum(
            spectrum, saturation, value, size, overall_value)


def _rgb_from_pixels(pixels, index):
    if fmtRGBA:
        return _rgb_from_pixels_rgba(pixels, index)
    else:  # probably BGRA
        return _rgb_from_pixels_rgba(pixels, index)[::-1]


def _rgb_from_pixels_rgba(pixels, index):
    return [pixels[index + i] for i in range(3)]


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
                    if useLegacyApi:
                        capture.waitForCaptureStateChangeEvent(200)
                        # we've got a capture event
                        if capture.getCaptureState() == xbmc.CAPTURE_STATE_DONE:
                            startReadOut = True
                    else:
                        vals = capture.getImage(200)
                        if len(vals) > 0 and player.playingvideo:
                            startReadOut = True
                    if startReadOut:
                        if useLegacyApi:
                            vals = capture.getImage()
                            screen = Screenshot(
                                vals, capture.getWidth(), capture.getHeight())
                        else:
                            screen = Screenshot(
                                capture.getImage(),
                                capture.getWidth(),
                                capture.getHeight())
                        hsvRatios = screen.spectrum_hsv(
                            screen.pixels, screen.capture_width, screen.capture_height)
                        if hue.settings.light == 0:
                            fade_light_hsv(hue.light, hsvRatios[0])
                        else:
                            for i, l in enumerate(hue.light):
                                # xbmc.sleep(4) #why?
                                fade_light_hsv(l, hsvRatios[i])
                except ZeroDivisionError:
                    logger.debuglog("no frame. looping.")

        if monitor.waitForAbort(0.1):
            # kodi requested an abort, lets get out of here.
            break

    del player  # might help with slow exit.


def fade_light_hsv(light, hsvRatio):
    fullSpectrum = light.fullSpectrum
    h, s, v = hsvRatio.hue(fullSpectrum)
    hvec = abs(h - light.hueLast) % int(65535/2)
    hvec = float(hvec/128.0)
    svec = s - light.satLast
    vvec = v - light.valLast
    # changed to squares for performance
    distance = math.sqrt(hvec**2 + svec**2 + vvec**2)
    if distance > 0:
        if hue.settings.ambilight_old_algorithm:
            duration = int(3 + 27 * distance/255)
        duration = int(10 - 2.5 * distance/255)
        light.set_light2(h, s, v, duration)

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
                if hue.settings.ambilight_dim_light == 0:
                    hue.ambilight_dim_light.brighter_light()
            elif hue.settings.ambilight_dim_light > 0:
                for l in hue.ambilight_dim_light:
                    l.brighter_light()
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

        if hue.settings.light == 0:  # group mode
            hue.light.get_current_setting()
        else:
            for l in hue.light:
                l.get_current_setting()  # loop through without sleep.

        if hue.settings.mode == 0:  # ambilight mode
            if hue.settings.ambilight_dim:
                if hue.settings.ambilight_dim_light == 0:
                    hue.ambilight_dim_light.get_current_setting()
                elif hue.settings.ambilight_dim_light > 0:
                    for l in hue.ambilight_dim_light:
                        l.get_current_setting()
            # start capture when playback starts
            capture_width = 32  # 100
            capture_height = capture_width / capture.getAspectRatio()
            if capture_height == 0:
                capture_height = capture_width  # fix for divide by zero.
            logger.debuglog("capture %s x %s" % (capture_width, capture_height))
            if useLegacyApi:
                capture.capture(
                    int(capture_width),
                    int(capture_height),
                    xbmc.CAPTURE_FLAG_CONTINUOUS)
            else:
                capture.capture(int(capture_width), int(capture_height))

    if (state == "started" and hue.pauseafterrefreshchange == 0) or state == "resumed":
        if hue.settings.mode == 0 and hue.settings.ambilight_dim:  # if in ambilight mode and dimming is enabled
            logger.debuglog("dimming for ambilight")
            if hue.settings.ambilight_dim_light == 0:
                hue.ambilight_dim_light.dim_light()
            elif hue.settings.ambilight_dim_light > 0:
                for l in hue.ambilight_dim_light:
                    l.dim_light()

        else:
            logger.debuglog("dimming lights")
            hue.dim_lights()
    elif state == "paused" and hue.last_state == "dimmed":
        # only if its coming from being off
        if hue.settings.mode == 0 and hue.settings.ambilight_dim:
            if hue.settings.ambilight_dim_light == 0:
                hue.ambilight_dim_light.partial_light()
            elif hue.settings.ambilight_dim_light > 0:
                for l in hue.ambilight_dim_light:
                    l.partial_light()
        else:
            hue.partial_lights()
    elif state == "stopped":
        if hue.settings.mode == 0 and hue.settings.ambilight_dim:
            if hue.settings.ambilight_dim_light == 0:
                hue.ambilight_dim_light.brighter_light()
            elif hue.settings.ambilight_dim_light > 0:
                for l in hue.ambilight_dim_light:
                    l.brighter_light()
        else:
            hue.brighter_lights()

if (__name__ == "__main__"):
    try:
        capture.getCaptureState()
    except AttributeError:
        useLegacyApi = False
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
