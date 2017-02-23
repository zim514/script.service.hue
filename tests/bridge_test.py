import bridge
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
GROUPS = {'lights': ['2', '1']}
NUPNP = [{'id': '12345', 'internalipaddress': '127.0.0.1'}]


@requests_mock.mock()
def test_user_exists_positive(m):
    m.register_uri('GET', 'http://127.0.0.1/api/fake/config',
                   json={'whitelist': ['fake']})
    assert bridge.user_exists(BRIDGE_IP, USERNAME, notify=False)


@requests_mock.mock()
def test_user_exists_negative(m):
    m.register_uri('GET', 'http://127.0.0.1/api/fake/config',
                   json={'whitelist': []})
    assert not bridge.user_exists(BRIDGE_IP, USERNAME, notify=False)


@requests_mock.mock()
def test_create_user(m):
    m.register_uri('POST', 'http://127.0.0.1/api',
                   json=[{'success': {'username': 'fake'}}])
    assert bridge.create_user(BRIDGE_IP, notify=False) == 'fake'
    assert m.last_request.json() == {'devicetype': 'kodi#ambilight'}


@requests_mock.mock()
def test_get_lights(m):
    m.register_uri('GET', 'http://127.0.0.1/api/fake/lights', json=LIGHTS)
    assert len(bridge.get_lights(BRIDGE_IP, USERNAME)) == 2


@requests_mock.mock()
def test_get_lights_by_ids(m):
    m.register_uri('GET', 'http://127.0.0.1/api/fake/lights', json=LIGHTS)
    assert len(bridge.get_lights_by_ids(BRIDGE_IP, USERNAME,
                                        light_ids=['1'])) == 1
    assert len(bridge.get_lights_by_ids(BRIDGE_IP, USERNAME,
                                        light_ids=['1', '2'])) == 2
    assert len(bridge.get_lights_by_ids(BRIDGE_IP, USERNAME)) == 2


@requests_mock.mock()
def test_get_lights_by_group(m):
    m.register_uri('GET', 'http://127.0.0.1/api/fake/groups/1', json=GROUPS)
    m.register_uri('GET', 'http://127.0.0.1/api/fake/lights', json=LIGHTS)
    assert len(bridge.get_lights_by_group(BRIDGE_IP, USERNAME, 1)) == 2


@requests_mock.mock()
def test_discover_nupnp(m):
    m.register_uri('GET', 'https://www.meethue.com/api/nupnp', json=NUPNP)
    assert bridge._discover_nupnp()
