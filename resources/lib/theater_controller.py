import lights
from tools import xbmclog


class TheaterController(lights.Controller):
    def __init__(self, *args, **kwargs):
        super(TheaterController, self).__init__(*args, **kwargs)

    def on_playback_start(self):
        # Let's keep only the last user-set state
        # BUT! Avoid theater subgroup if enabled
        subgroup = None
        if self.settings.theater_pause_dim_subgroup:
            subgroup = self.settings.theater_subgroup.split(',')
        self.save_state_as_initial(subgroup)

        # Theater dimming
        xbmclog('Kodi Hue: In TheaterController.on_playback_start() '
                'dimming theater group')
        self.set_state(
            bri=self.settings.theater_start_bri,
            force_on=self.settings.force_light_on,
        )

    def on_playback_pause(self):
        if self.settings.theater_pause_dim_subgroup:
            xbmclog('Kodi Hue: In TheaterController.on_playback_pause() '
                    'undimming theater subgroup')
            if self.settings.theater_pause_bri_override:
                self.set_state(
                    bri=self.settings.theater_pause_bri,
                    lights=self.settings.theater_subgroup.split(','),
                    force_on=self.settings.force_light_on,
                )
            else:
                self.restore_initial_state(
                    lights=self.settings.theater_subgroup.split(','),
                    force_on=self.settings.force_light_on,
                )
        else:
            xbmclog('Kodi Hue: In TheaterController.on_playback_pause() '
                    'undimming theater group')
            if self.settings.theater_pause_bri_override:
                self.set_state(
                    bri=self.settings.theater_pause_bri,
                    force_on=self.settings.force_light_on,
                )
            else:
                self.restore_initial_state(
                    force_on=self.settings.force_light_on,
                )

    def on_playback_stop(self):
        xbmclog('Kodi Hue: In TheaterController.on_playback_stop() '
                'undimming theater group')
        if self.settings.theater_stop_bri_override:
            self.set_state(
                bri=self.settings.theater_stop_bri,
                force_on=self.settings.force_light_on,
            )
        else:
            self.restore_initial_state(
                force_on=self.settings.force_light_on,
            )
