import json
import requests
import time


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
            self.hue = self.init_hue
        except KeyError:
            self.livingwhite = True

        try:
            self.init_sat = spec['state']['sat']
            self.sat = self.init_sat
        except KeyError:
            self.livingwhite = True

        self.init_bri = spec['state']['bri']
        self.bri = self.init_bri

        self.init_on = spec['state']['on']
        self.on = self.init_on

        self.session = requests.Session()

    def set_state(self, hue=None, sat=None, bri=None, on=None,
                  transition_time=None):
        state = {}
        if hue is not None and not self.livingwhite and hue != self.hue:
            self.hue = hue
            state['hue'] = hue
        if sat is not None and not self.livingwhite and sat != self.sat:
            self.sat = sat
            state['sat'] = sat
        if bri is not None and bri != self.bri:
            self.bri = bri
            state['bri'] = bri
        if on is not None and on != self.on:
            self.on = on
            state['on'] = on
        if transition_time is not None:
            state['transitiontime'] = transition_time

        data = json.dumps(state)
        try:
            endpoint = 'http://{}/api/{}/lights/{}/state'.format(
                self.bridge_ip, self.username, self.light_id)
            self.session.put(endpoint, data)
        except Exception:
            pass

    def restore_initial_state(self, transition_time=0):
        self.set_state(
            self.init_hue,
            self.init_sat,
            self.init_bri,
            self.init_on,
            transition_time
        )

    def save_state_as_initial(self):
        self.init_hue = self.hue
        self.init_sat = self.sat
        self.init_bri = self.bri
        self.init_on = self.on

    def __repr__(self):
        return ('<Light({}) {} hue: {}, sat: {}, bri: {}, on: {}>'.format(
            self.name, self.light_id, self.hue, self.sat, self.bri, self.on))


class Controller(list):

    def __init__(self, lights, settings):
        self.lights = lights
        self.settings = settings

    def set_state(self, hue=None, sat=None, bri=None, on=None,
                  transition_time=None):
        for light in self.lights:
            if not self.settings.force_light_on and not light.init_on:
                continue
            if bri:
                if self.settings.proportional_dim_time:
                    transition_time = self._transition_time(light, bri)
                else:
                    transition_time = self.settings.dim_time

            light.set_state(
                hue=hue, sat=sat, bri=bri, on=on,
                transition_time=transition_time
            )

    def restore_initial_state(self):
        for light in self.lights:
            if not self.settings.force_light_on and not light.init_on:
                continue
            transition_time = self.settings.dim_time
            if self.settings.proportional_dim_time:
                transition_time = self._transition_time(light, light.init_bri)

            light.restore_initial_state(
                transition_time
            )

    def save_state_as_initial(self):
        for light in self.lights:
            light.save_state_as_initial()

    def flash_lights(self):
        self.dim_lights()
        time.sleep(self.settings.dim_time / 10)
        self.undim_lights()

    def _transition_time(self, light, bri):
        time = 0

        difference = abs(float(bri) - light.bri)
        total = float(light.init_bri) - self.settings.theater_start_bri
        if total == 0:
            return self.settings.dim_time
        proportion = difference / total
        time = int(round(proportion * self.settings.dim_time))

        return time
