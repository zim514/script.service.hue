from threading import Event
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

from settings import Settings
from tools import get_version
from ambilight_controller import AmbilightController
import bridge
import ui
import lights
import algorithm
import image

xbmc.log("Kodi Hue: DEBUG service started, version: %s" % get_version())

ev = Event()
capture = xbmc.RenderCapture()
fmt = capture.getImageFormat()
# BGRA or RGBA
fmtRGBA = fmt == 'RGBA'


class MyMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        hue.settings.readxml()
        hue.update_controllers()


class MyPlayer(xbmc.Player):
    duration = 0
    playingvideo = False
    playlistlen = 0
    movie = False

    def __init__(self):
        xbmc.log('Kodi Hue: DEBUG Player instantiated')
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        xbmc.log("Kodi Hue: DEBUG playback started called on player")
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playlistlen = playlist.size()
        self.playingvideo = True
        state_changed("started", self.duration)

    def onPlayBackPaused(self):
        xbmc.log("Kodi Hue: DEBUG playback paused called on player")
        ev.set()
        state_changed("paused", self.duration)
        if self.isPlayingVideo():
            self.playingvideo = False

    def onPlayBackResumed(self):
        xbmc.log("Kodi Hue: DEBUG playback resume called on player")
        state_changed("resumed", self.duration)
        ev.clear()
        if self.isPlayingVideo():
            self.playingvideo = True
            if self.duration == 0:
                self.duration = self.getTotalTime()

    def onPlayBackStopped(self):
        xbmc.log("Kodi Hue: DEBUG playback stopped called on player")
        ev.set()
        state_changed("stopped", self.duration)
        self.playingvideo = False
        self.playlistlen = 0

    def onPlayBackEnded(self):
        ev.set()
        xbmc.log("Kodi Hue: DEBUG playback ended called on player")
        # If there are upcoming plays, ignore
        if self.playlistpos < self.playlistlen-1:
            ev.clear()
            return

        self.playingvideo = False
        state_changed("stopped", self.duration)


class Hue:
    theater_controller = None
    ambilight_controller = None
    static_controller = None

    def __init__(self, settings, args):
        self.settings = settings
        self.connected = False

        try:
            params = dict(arg.split("=") for arg in args.split("&"))
        except Exception:
            params = {}

        if params == {}:
            # if there's a bridge IP, try to talk to it.
            if self.settings.bridge_ip not in ["-", "", None]:
                result = bridge.user_exists(
                    self.settings.bridge_ip,
                    self.settings.bridge_user
                )
                if result:
                    self.connected = True
                    self.update_controllers()
        elif params['action'] == "discover":
            ui.discover_hue_bridge(self)
        elif params['action'] == "reset_settings":
            os.unlink(os.path.join(__addondir__, "settings.xml"))
        elif params['action'] == "setup_theater_lights":
            ret = ui.multiselect_lights(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                'Select Theater Lights',
                ','.join([self.settings.ambilight_group,
                          self.settings.static_group]),
                self.settings.theater_group
            )
            self.settings.update(theater_group=ret)
            self.update_controllers()
        elif params['action'] == "setup_theater_subgroup":
            ret = ui.multiselect_lights(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                'Select Theater Subgroup',
                ','.join([self.settings.ambilight_group,
                          self.settings.static_group]),
                self.settings.theater_subgroup
            )
            self.settings.update(theater_subgroup=ret)
            self.update_controllers()
        elif params['action'] == "setup_ambilight_lights":
            ret = ui.multiselect_lights(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                'Select Ambilight Lights',
                ','.join([self.settings.theater_group,
                          self.settings.static_group]),
                self.settings.ambilight_group
            )
            self.settings.update(ambilight_group=ret)
            self.update_controllers()
        elif params['action'] == "setup_static_lights":
            ret = ui.multiselect_lights(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                'Select Static Lights',
                ','.join([self.settings.theater_group,
                          self.settings.ambilight_group]),
                self.settings.static_group
            )
            self.settings.update(static_group=ret)
            self.update_controllers()
        else:
            # not yet implemented
            pass

        if self.connected:
            if self.settings.misc_initialflash:
                self.ambilight_controller.flash_lights()
                self.theater_controller.flash_lights()

    def update_controllers(self):
        self.ambilight_controller = AmbilightController(
            bridge.get_lights_by_ids(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                self.settings.ambilight_group.split(',')),
            self.settings
        )

        self.theater_controller = lights.Controller(
            bridge.get_lights_by_ids(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                self.settings.theater_group.split(',')),
            self.settings
        )

        self.static_controller = lights.Controller(
            bridge.get_lights_by_ids(
                self.settings.bridge_ip,
                self.settings.bridge_user,
                self.settings.static_group.split(',')),
            self.settings
        )

        xbmc.log(
            'Kodi Hue: DEBUG instantiated controllers with following lights '
            '- theater: {} ambilight: {} static: {}'.format(
                self.theater_controller.lights,
                self.ambilight_controller.lights,
                self.static_controller.lights,
            )
        )


def run():
    player = MyPlayer()
    if player is None:
        xbmc.log('Kodi Hue: DEBUG Could not instantiate player')
        return

    while not monitor.abortRequested():
        if len(hue.ambilight_controller.lights) and not ev.is_set():
            startReadOut = False
            vals = {}
            # live tv does not trigger playbackstart
            if player.isPlayingVideo() and not player.playingvideo:
                player.playingvideo = True

                # We will be saving state of the lights, do not interfere yet
                ev.set()
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
                        hsv_ratios = screen.spectrum_hsv(
                            screen.pixels,
                            hue.settings.ambilight_threshold_value,
                            hue.settings.ambilight_threshold_saturation,
                            hue.settings.color_bias,
                            len(hue.ambilight_controller.lights)
                        )
                        for i in range(len(hue.ambilight_controller.lights)):
                            algorithm.transition_colorspace(
                                hue, hue.ambilight_controller.lights.values()[i], hsv_ratios[i],
                            )
                except ZeroDivisionError:
                    pass

        if monitor.waitForAbort(0.1):
            xbmc.log('Kodi Hue: DEBUG deleting player')
            del player  # might help with slow exit.


def state_changed(state, duration):
    xbmc.log('Kodi Hue: DEBUG State changed to {}'.format(state))

    if (xbmc.getCondVisibility('Window.IsActive(screensaver-atv4.xml)') or
        xbmc.getCondVisibility('Window.IsActive(screensaver-video-main.xml)')):
        return

    if duration < hue.settings.misc_disableshort_threshold and hue.settings.misc_disableshort:
        return

    if state == "started":
        # start capture when playback starts
        capture_width = 32  # 100
        capture_height = capture_width / capture.getAspectRatio()
        if capture_height == 0:
            capture_height = capture_width  # fix for divide by zero.
        capture.capture(int(capture_width), int(capture_height))

    if state == "started" or state == "resumed":

        # Let's keep only the last user-set state
        # BUT! Avoid theater subgroup if enabled
        theater_subgroup = None
        if hue.settings.theater_pause_dim_subgroup:
            theater_subgroup = hue.settings.theater_subgroup.split(',')
        hue.theater_controller.save_state_as_initial(theater_subgroup)

        hue.ambilight_controller.on_playback_start()

        # Theater dimming
        xbmc.log('Kodi Hue: DEBUG dimming theater group')
        hue.theater_controller.set_state(
            bri=hue.settings.theater_start_bri,
            force_on=hue.settings.force_light_on,
        )

        # Static group turn on
        xbmc.log('Kodi Hue: DEBUG turning on static group')
        h = None
        if hue.settings.static_start_hue_override:
            h = hue.settings.static_start_hue

        sat = None
        if hue.settings.static_start_sat_override:
            sat = hue.settings.static_start_sat

        hue.static_controller.set_state(
            hue=h,
            sat=sat,
            bri=hue.settings.static_start_bri,
            on=True,
        )

        ev.clear()

    elif state == "paused":
        hue.ambilight_controller.on_playback_pause()

        # Theather dimming
        if settings.theater_pause_dim_subgroup:
            xbmc.log('Kodi Hue: DEBUG undimming theater subgroup')
            if hue.settings.theater_pause_bri_override:
                hue.theater_controller.set_state(
                    bri=hue.settings.theater_pause_bri,
                    lights=hue.settings.theater_subgroup.split(','),
                    force_on=hue.settings.force_light_on,
                )
            else:
                hue.theater_controller.restore_initial_state(
                    lights=hue.settings.theater_subgroup.split(','),
                    force_on=hue.settings.force_light_on,
                )
        else:
            xbmc.log('Kodi Hue: DEBUG undimming theater group')
            if hue.settings.theater_pause_bri_override:
                hue.theater_controller.set_state(
                    bri=hue.settings.theater_pause_bri,
                    force_on=hue.settings.force_light_on,
                )
            else:
                hue.theater_controller.restore_initial_state(
                    force_on=hue.settings.force_light_on,
                )

        # Static off
        hue.static_controller.set_state(
            on=False,
        )

    elif state == "stopped":
        hue.ambilight_controller.on_playback_stop()

        # Theater dimming
        xbmc.log('Kodi Hue: DEBUG undimming theater group')
        if hue.settings.theater_stop_bri_override:
            hue.theater_controller.set_state(
                bri=hue.settings.theater_stop_bri,
                force_on=hue.settings.force_light_on,
            )
        else:
            hue.theater_controller.restore_initial_state(
                force_on=hue.settings.force_light_on,
            )

        # Static restore
        hue.static_controller.restore_initial_state()

if (__name__ == "__main__"):
    settings = Settings()
    monitor = MyMonitor()

    args = None
    if len(sys.argv) == 2:
        args = sys.argv[1]
    hue = Hue(settings, args)
    while not hue.connected and not monitor.abortRequested():
        time.sleep(1)
    run()
