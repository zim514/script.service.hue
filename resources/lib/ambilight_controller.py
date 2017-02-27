import lights
from tools import xbmclog


class AmbilightController(lights.Controller):
    def __init__(self, *args, **kwargs):
        super(AmbilightController, self).__init__(*args, **kwargs)

    def on_playback_start(self):
        if self.settings.ambilight_start_dim_enable:
            self.save_state_as_initial()

            xbmclog('Kodi Hue: In AmbilightController.on_playback_start() '
                    'dimming ambilight group')
            self.set_state(
                bri=self.settings.ambilight_start_dim,
                force_on=self.settings.force_light_on,
            )

    def on_playback_pause(self):
        if self.settings.ambilight_start_dim_enable:
            xbmclog('Kodi Hue: In AmbilightController.on_playback_pause() '
                    'undimming ambilight group')
            if self.settings.ambilight_pause_bri_override:
                bri = self.settings.ambilight_pause_bri
                self.set_state(
                    bri=bri,
                    force_on=self.settings.force_light_on,
                )
            else:
                self.restore_initial_state(
                    force_on=self.settings.force_light_on,
                )

    def on_playback_stop(self):
        if self.settings.ambilight_start_dim_enable:
            xbmclog('Kodi Hue: In AmbilightController.on_playback_stop() '
                    'undimming ambilight group')
            if self.settings.ambilight_stop_bri_override:
                self.set_state(
                    bri=self.settings.ambilight_stop_bri,
                    force_on=self.settings.force_light_on,
                )
            else:
                self.restore_initial_state(
                    force_on=self.settings.force_light_on,
                )
        else:
            self.restore_initial_state(
                    force_on=self.settings.force_light_on,
            )
