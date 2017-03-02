import lights
import requests_mock


BRIDGE_IP = '127.0.0.1'
USERNAME = 'fake'
LIGHTS = {u'1': {u'name': u'fake',
                 u'state': {u'alert': u'none',
                            u'bri': 254,
                            u'hue': 17738,
                            u'on': True,
                            u'sat': 100},
                 u'type': u'Extended color light'},
          u'2': {u'name': u'fake',
                 u'state': {u'alert': u'none',
                            u'bri': 254,
                            u'on': True},
                 u'type': u'Not a color light'}}


def test_init_color():
    light = lights.Light(BRIDGE_IP, USERNAME, 1, LIGHTS['1'])

    assert light.hue == light.init_hue == 17738
    assert light.sat == light.init_sat == 100
    assert light.bri == light.init_bri == 254
    assert light.on is light.init_on is True
    assert light.livingwhite is False


def test_init_white():
    light = lights.Light(BRIDGE_IP, USERNAME, 2, LIGHTS['2'])

    assert light.bri == light.init_bri == 254
    assert light.on is light.init_on is True
    assert light.livingwhite is True


@requests_mock.mock()
def test_set_state(m):
    light = lights.Light(BRIDGE_IP, USERNAME, 1, LIGHTS['1'])
    m.register_uri('PUT', 'http://127.0.0.1/api/fake/lights/1/state')

    light.set_state(hue=47)
    assert light.hue == 47
    assert light.sat == 100
    assert light.bri == 254
    assert light.on is True

    assert m.last_request.json() == {'hue': 47}

    light.set_state(hue=47, sat=12, on=False)
    assert light.hue == 47
    assert light.sat == 12
    assert light.bri == 254
    assert light.on is False

    assert m.last_request.json() == {u'on': False, u'sat': 12}

    light.set_state(hue=47, sat=99, bri=15, on=False, transition_time=321)
    assert light.hue == 47
    assert light.sat == 99
    assert light.bri == 15
    assert light.on is False

    assert m.last_request.json() == {u'bri': 15, u'sat': 99,
                                     u'transitiontime': 321}

    assert light.init_hue == 17738
    assert light.init_sat == 100
    assert light.init_bri == 254
    assert light.init_on is True

    light.restore_initial_state()
    assert light.hue == 17738
    assert light.sat == 100
    assert light.bri == 254
    assert light.on is True

    assert m.last_request.json() == {u'bri': 254, u'hue': 17738, u'on': True,
                                     u'sat': 100, u'transitiontime': 0}
