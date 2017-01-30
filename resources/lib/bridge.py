import tools

try:
    import requests
except ImportError:
    tools.notify("Kodi Hue", "ERROR: Could not import Python requests")


def user_exists(bridge_ip, bridge_user):
    req = requests.get('http://{}/api/{}/config'.format(
        bridge_ip, bridge_user))
    res = req.json()

    success = False
    try:
        success = bridge_user in res['whitelist']
    except KeyError:
        success = False

    if success:
        tools.notify("Kodi Hue", "Connected")
    else:
        tools.notify("Kodi Hue", "Could not connect to bridge")

    return success
