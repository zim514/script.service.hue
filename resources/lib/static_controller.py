import lights
from tools import xbmclog


class StaticController(lights.Controller):
    def __init__(self, *args, **kwargs):
        super(StaticController, self).__init__(*args, **kwargs)

    def on_playback_start(self):
        xbmclog('Kodi Hue: DEBUG turning on static group')
        hue = None
        if self.settings.static_start_hue_override:
            hue = self.settings.static_start_hue

        sat = None
        if self.settings.static_start_sat_override:
            sat = self.settings.static_start_sat

        self.set_state(
            hue=hue,
            sat=sat,
            bri=self.settings.static_start_bri,
            on=True,
        )

    def on_playback_pause(self):
        self.set_state(
            on=False,
        )

    def on_playback_stop(self):
        self.restore_initial_state()
