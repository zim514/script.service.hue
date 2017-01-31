import json
import requests
import time

import xbmc


class Light(object):

    def __init__(self, bridge_ip, username, light_id, spec):
        self.bridge_ip = bridge_ip
        self.username = username

        self.light_id = light_id
        self.fullspectrum = ((spec['type'] == 'Color Light') or
                             (spec['type'] == 'Extended Color Light'))
        self.livingwhite = False
        self.name = spec['name']

        try:
            self.init_hue = spec['state']['hue']
            self.last_hue = self.init_hue
            self.hue = self.init_hue
        except KeyError:
            self.livingwhite = True

        try:
            self.init_sat = spec['state']['sat']
            self.last_sat = self.init_sat
            self.sat = self.init_sat
        except KeyError:
            self.livingwhite = True

        self.init_bri = spec['state']['bri']
        self.last_bri = self.init_bri
        self.bri = self.init_bri

        self.init_on = spec['state']['on']
        self.last_on = self.init_on
        self.on = self.init_on

        self.session = requests.Session()

    def set_state(self, hue=None, sat=None, bri=None, on=None,
                  transition_time=None):
        state = {}
        if hue is not None and not self.livingwhite and hue != self.last_hue:
            self.hue = hue
            self.last_hue = hue
            state['hue'] = hue
        if sat is not None and not self.livingwhite and sat != self.last_sat:
            self.sat = sat
            self.last_sat = sat
            state['sat'] = sat
        if bri is not None and bri != self.last_bri:
            self.bri = bri
            self.last_bri = bri
            state['bri'] = bri
        if on is not None and on != self.last_on:
            self.on = on
            self.last_on = on
            state['on'] = on
        if transition_time is not None:
            state['transitiontime'] = transition_time

        data = json.dumps(state)
        try:
            endpoint = 'http://{}/api/{}/lights/{}/state'.format(
                self.bridge_ip, self.username, self.light_id)
            xbmc.log("Kodi Hue: DEBUG light transition {} {}".format(endpoint,
                                                                     data))
            self.session.put(endpoint, data)
        except Exception:
            pass

    def set_initial_state(self):
        self.set_state(
            self.init_hue,
            self.init_sat,
            self.init_bri,
            self.init_on)

    def __repr__(self):
        return ('<Light {} hue: {}, sat: {}, bri: {}, on: {}>'.format(
            self.light_id, self.hue, self.sat, self.bri, self.on))


class Controller(list):

    def __init__(self, lights, settings):
        self.lights = lights
        self.settings = settings

    def partial_lights(self):
        if self.settings.override_paused:
            bri = self.settings.paused_bri

            for light in self.lights:
                sat = None
                hue = None

                if self.settings.override_sat:
                    sat = self.settings.undim_sat
                else:
                    sat = light.init_sat

                if self.settings.override_hue:
                    hue = self.settings.undim_hue
                else:
                    hue = light.init_hue

                light.set_state(
                    hue=hue, sat=sat, bri=bri,
                    transition_time=self._transition_time(light, bri)
                )
        else:
            # not enabled for dimming on pause
            self.undim_lights()

    def undim_lights(self):
        for light in self.lights:
            if self.settings.override_undim_bri:
                bri = self.settings.undim_bri
            else:
                bri = light.init_bri

            sat = None
            hue = None

            if self.settings.override_sat:
                sat = self.settings.undim_sat
            else:
                sat = light.init_sat
            if self.settings.override_hue:
                hue = self.settings.undim_hue
            else:
                hue = light.init_hue

            light.set_state(
                hue=hue, sat=sat, bri=bri,
                transition_time=self._transition_time(light, bri)
            )

    def dim_lights(self):
        xbmc.log('Kodi Hue: DEBUG Controller.dim_lights {}'.format(self.lights))
        for light in self.lights:
            hue = None
            if self.settings.override_hue:
                hue = self.settings.dimmed_hue

            sat = None
            if self.settings.override_sat:
                sat = self.settings.dimmed_sat

            light.set_state(
                hue=hue, sat=sat, bri=self.settings.dimmed_bri,
                transition_time=self._transition_time(
                    light, self.settings.dimmed_bri)
            )

    def flash_lights(self):
        self.dim_lights()
        time.sleep(self.settings.dim_time / 10)
        self.undim_lights()

    def _transition_time(self, light, bri):
        time = 0

        if self.settings.proportional_dim_time:
            difference = abs(float(bri) - light.last_bri)
            total = float(light.init_bri) - self.settings.dimmed_bri
            proportion = difference / total
            time = int(round(proportion * self.settings.dim_time))
        else:
            time = self.settings.dim_time

        return time
