import random

import lights
from tools import xbmclog


class StaticController(lights.Controller):
    def __init__(self, *args, **kwargs):
        super(StaticController, self).__init__(*args, **kwargs)

    def on_playback_start(self):
        xbmclog('Kodi Hue: In StaticController.on_playback_start() '
                'turning on static group')
        hue = None
        if self.settings.static_start_hue_override:
            hue = self.settings.static_start_hue

        sat = None
        if self.settings.static_start_sat_override:
            sat = self.settings.static_start_sat

        if self.settings.static_start_random:
            hue = random.randint(0, 65535)
            sat = random.randint(100, 254)

        self.set_state(
            hue=hue,
            sat=sat,
            bri=self.settings.static_start_bri,
            on=True,
        )

    def on_playback_pause(self):
        xbmclog('Kodi Hue: In StaticController.on_playback_pause() '
                'turning off static group')
        self.set_state(
            on=False,
        )

    def on_playback_stop(self):
        xbmclog('Kodi Hue: In StaticController.on_playback_pause() '
                'restoring static group')
        self.restore_initial_state()
