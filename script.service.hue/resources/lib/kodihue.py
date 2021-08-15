import json
from datetime import timedelta
from socket import getfqdn

import requests
import xbmc
import xbmcgui

from resources.lib.qhue.qhue import QhueException
from . import ADDON, QHUE_TIMEOUT, SETTINGS_CHANGED, reporting
from . import kodigroup
from . import qhue, ADDONID, cache
from .kodisettings import read_settings
from .kodisettings import settings_storage
from .language import get_string as _


def create_hue_scene(bridge):
    xbmc.log("[script.service.hue] In kodiHue createHueScene")
    scenes = bridge.scenes

    xbmcgui.Dialog().ok(heading=_("Create New Scene"), message=_("Adjust lights to desired state in the Hue App to save as new scene.[CR]Set a fade time in seconds, or set to 0 seconds for an instant transition."))

    scene_name = xbmcgui.Dialog().input(_("Scene Name"))

    if scene_name:
        transition_time = int(xbmcgui.Dialog().numeric(0, _("Fade Time (Seconds)"), defaultt="10")) * 10  # yes, default with two ts. *10 to convert to msecs
        if transition_time > 65534:  # hue uses uint16 for transition time.
            transition_time = 65534
        selected = select_hue_lights(bridge)

        if selected:
            result = scenes(lights=selected, name=scene_name, recycle=False, type='LightScene', http_method='post', transitiontime=transition_time)
            # xbmc.log("[script.service.hue] In kodiHue createHueScene. Res: {}".format(res))
            if result[0]["success"]:
                xbmcgui.Dialog().ok(heading=_("Create New Scene"), message=_("Scene successfully created![CR]You may now assign your Scene to player actions."))
            else:
                xbmcgui.Dialog().ok(_("Error"), _("Scene not created."))
    else:
        xbmcgui.Dialog().ok(_("Error"), _("Scene not created."))


def delete_hue_scene(bridge):
    xbmc.log("[script.service.hue] In kodiHue deleteHueScene")
    scene = select_hue_scene(bridge)
    if scene is not None:
        confirm = xbmcgui.Dialog().yesno(heading=_("Delete Hue Scene"), message=_("Are you sure you want to delete this scene:[CR]" + str(scene[1])))
    if scene and confirm:
        scenes = bridge.scenes
        res = scenes[scene[0]](http_method='delete')
        xbmc.log("[script.service.hue] In kodiHue createHueGroup. Res: {}".format(res))
        if res[0]["success"]:
            notification(_("Hue Service"), _("Scene deleted"))
        else:
            notification(_("Hue Service"), _("ERROR: Scene not created"))


def _discover_nupnp():
    xbmc.log("[script.service.hue] In kodiHue discover_nupnp()")
    try:
        req = requests.get('https://discovery.meethue.com/')
    except requests.RequestException as exc:
        xbmc.log("[script.service.hue] Nupnp failed: {}".format(exc))
        return None

    res = req.json()
    bridge_ip = None
    if res:
        bridge_ip = res[0]["internalipaddress"]
    return bridge_ip


def _discover_ssdp():
    from . import ssdp
    from urllib.parse import urlsplit

    try:
        ssdp_list = ssdp.discover("upnp:rootdevice", timeout=10, mx=5)
    except Exception as exc:
        xbmc.log("[script.service.hue] SSDP error: {}".format(exc.args))
        notification(_("Hue Service"), _("Network not ready"), xbmcgui.NOTIFICATION_ERROR)
        return None

    xbmc.log("[script.service.hue] ssdp_list: {}".format(ssdp_list))

    bridges = [u for u in ssdp_list if 'IpBridge' in u.server]
    if bridges:
        ip = urlsplit(bridges[0].location).hostname
        xbmc.log("[script.service.hue] ip: {}".format(ip))
        return ip
    return None


def discover_bridge(monitor):
    xbmc.log("[script.service.hue] Start bridgeDiscover")
    # Create new config if none exists. Returns success or fail as bool
    ADDON.setSettingString("bridgeIP", "")
    ADDON.setSettingString("bridgeUser", "")
    settings_storage['connected'] = False

    progressBar = xbmcgui.DialogProgress()
    progressBar.create(_('Searching for bridge...'))
    progressBar.update(5, _("Discovery started"))

    complete = False
    while not progressBar.iscanceled() and not complete and not monitor.abortRequested():

        progressBar.update(percent=10, message=_("N-UPnP discovery..."))
        bridgeIP = _discover_nupnp()

        if not bridgeIP:
            progressBar.update(percent=20, message=_("UPnP discovery..."))
            bridgeIP = _discover_ssdp()

        if connection_test(bridgeIP):
            progressBar.update(percent=100, message=_("Found bridge: ") + bridgeIP)
            monitor.waitForAbort(1)

            bridgeUser = create_user(monitor, bridgeIP, progressBar)

            if bridgeUser:
                xbmc.log("[script.service.hue] User created: {}".format(bridgeUser))
                progressBar.update(percent=90, message=_("User Found![CR]Saving settings..."))

                ADDON.setSettingString("bridgeIP", bridgeIP)
                ADDON.setSettingString("bridgeUser", bridgeUser)
                complete = True
                settings_storage['connected'] = True
                progressBar.update(percent=100, message=_("Complete!"))
                monitor.waitForAbort(5)
                progressBar.close()
                xbmc.log("[script.service.hue] Bridge discovery complete")
                return True

            xbmc.log("[script.service.hue] User not created, received: {}".format(bridgeUser))
            progressBar.update(percent=100, message=_("User not found[CR]Check your bridge and network."))
            monitor.waitForAbort(5)
            complete = True
            progressBar.close()

        else:
            progressBar.update(percent=100, message=_("Bridge not found[CR]Check your bridge and network."))
            xbmc.log("[script.service.hue] Bridge not found, check your bridge and network")
            monitor.waitForAbort(5)
            complete = True
            progressBar.close()

    if progressBar.iscanceled():
        xbmc.log("[script.service.hue] Bridge discovery cancelled by user")
        progressBar.update(100, _("Cancelled"))
        complete = True
        progressBar.close()


def connection_test(bridge_ip):
    b = qhue.qhue.Resource("http://{}/api".format(bridge_ip), requests.session())
    try:
        apiversion = b.config()['apiversion']
    except qhue.QhueException as error:
        xbmc.log("[script.service.hue] Connection test failed.  {}: {}".format(error.type_id, error.message))
        reporting.process_exception(error.type_id, error.message)
        return False
    except requests.RequestException as error:
        xbmc.log("[script.service.hue] Connection test failed.  {}".format(error))
        reporting.process_exception(error)
        return False
    except KeyError as error:
        notification(_("Hue Service"), _("Bridge API: {}, update your bridge".format(apiversion)), icon=xbmcgui.NOTIFICATION_ERROR)
        xbmc.log("[script.service.hue] in ConnectionTest():  Connected! Bridge too old: {}, error: {}".format(apiversion, error))
        return False

    api_split = apiversion.split(".")

    if apiversion and int(api_split[0]) >= 1 and int(api_split[1]) >= 38:  # minimum bridge version 1.38
        xbmc.log("[script.service.hue] Bridge Found! Hue API version: {}".format(apiversion))
        return True

    notification(_("Hue Service"), _("Bridge API: {}, update your bridge".format(apiversion)), icon=xbmcgui.NOTIFICATION_ERROR)
    xbmc.log("[script.service.hue] in ConnectionTest():  Connected! Bridge too old: {}".format(apiversion))
    return False


def user_test(bridgeIP, bridgeUser):
    xbmc.log("[script.service.hue] in ConnectionTest() Attempt initial connection")
    b = qhue.Bridge(bridgeIP, bridgeUser, timeout=QHUE_TIMEOUT)
    try:
        zigbeechan = b.config()['zigbeechannel']
    except (requests.RequestException, qhue.QhueException, KeyError):
        return False

    if zigbeechan:
        xbmc.log("[script.service.hue] Hue User Authorized. Bridge Zigbee Channel: {}".format(zigbeechan))
        return True
    return False


def discover_bridge_ip(monitor):
    # discover hue bridge IP silently for non-interactive discovery / bridge IP change.
    xbmc.log("[script.service.hue] In discoverBridgeIP")
    bridgeIP = _discover_nupnp()
    if connection_test(bridgeIP):
        return bridgeIP

    bridgeIP = _discover_ssdp()
    if connection_test(bridgeIP):
        return bridgeIP

    return False


def create_user(monitor, bridgeIP, progressBar=False):
    xbmc.log("[script.service.hue] In createUser")
    # device = 'kodi#'+getfqdn()
    data = '{{"devicetype": "kodi#{}"}}'.format(
        getfqdn())  # Create a devicetype named kodi#localhostname. Eg: kodi#LibreELEC

    req = requests
    res = 'link button not pressed'
    timeout = 0
    progress = 0
    if progressBar:
        progressBar.update(percent=progress, message=_("Press link button on bridge. Waiting for 90 seconds..."))  # press link button on bridge

    while 'link button not pressed' in res and timeout <= 90 and not monitor.abortRequested() and not progressBar.iscanceled():
        xbmc.log("[script.service.hue] In create_user: abortRquested: {}, timer: {}".format(str(monitor.abortRequested()), timeout))

        if progressBar:
            progressBar.update(percent=progress, message=_("Press link button on bridge"))  # press link button on bridge

        try:
            req = requests.post('http://{}/api'.format(bridgeIP), data=data)
        except requests.exceptions.RequestException as exc:
            xbmc.log("[script.service.hue] requests exception: {}".format(exc))
            return False
        except Exception as exc:
            xbmc.log("[script.service.hue] requests exception: {}".format(exc))
            reporting.process_exception(exc)
            return False

        res = req.text
        monitor.waitForAbort(1)
        timeout = timeout + 1
        progress = progress + 1

    res = req.json()
    xbmc.log("[script.service.hue] json response: {}, content: {}".format(res, req.content))

    try:
        username = res[0]['success']['username']
        return username
    except Exception as exc:
        xbmc.log("[script.service.hue] Username exception: {}".format(exc))
        return False


def configure_scene(bridge, kGroupID, action):
    scene = select_hue_scene(bridge)
    if scene is not None:
        # group0_startSceneID
        ADDON.setSettingString("group{}_{}SceneID".format(kGroupID, action), scene[0])
        ADDON.setSettingString("group{}_{}SceneName".format(kGroupID, action), scene[1])
        ADDON.openSettings()


def configure_ambilights(bridge, kGroupID):
    lights = select_hue_lights(bridge)
    lightNames = []
    colorLights = []
    if lights is not None:
        for L in lights:
            # gamut = getLightGamut(bridge, L)
            # if gamut == "A" or gamut== "B" or gamut == "C": #defaults to C if unknown model
            lightNames.append(get_light_name(bridge, L))
            colorLights.append(L)

        ADDON.setSettingString("group{}_Lights".format(kGroupID), ','.join(colorLights))
        ADDON.setSettingString("group{}_LightNames".format(kGroupID), ','.join(lightNames))
        ADDON.setSettingBool("group{}_enabled".format(kGroupID), True)
        ADDON.openSettings()


def get_light_name(bridge, L):
    try:
        name = bridge.lights()[L]['name']
    except Exception:
        xbmc.log("[script.service.hue] getLightName Exception")
        return None

    if name is None:
        return None
    return name


def select_hue_lights(bridge):
    xbmc.log("[script.service.hue] In selectHueLights{}")
    hueLights = bridge.lights()

    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    items = []
    index = []
    lightIDs = []

    for light in hueLights:
        hLight = hueLights[light]
        hLightName = hLight['name']

        # xbmc.log("[script.service.hue] In selectHueGroup: {}, {}".format(hgroup,name))
        index.append(light)
        items.append(xbmcgui.ListItem(label=hLightName))

    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    selected = xbmcgui.Dialog().multiselect(_("Select Hue Lights..."), items)
    if selected:
        # id = index[selected]
        for s in selected:
            lightIDs.append(index[s])

    xbmc.log("[script.service.hue] lightIDs: {}".format(lightIDs))

    if lightIDs:
        return lightIDs
    return None


def select_hue_scene(bridge):
    xbmc.log("[script.service.hue] In selectHueScene{}")
    hueScenes = bridge.scenes()

    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    items = []
    index = []
    selectedId = -1

    for scene in hueScenes:

        hScene = hueScenes[scene]
        hSceneName = hScene['name']

        if hScene['version'] == 2 and hScene["recycle"] is False and hScene["type"] == "LightScene":
            index.append(scene)
            items.append(xbmcgui.ListItem(label=hSceneName))

    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    selected = xbmcgui.Dialog().select("Select Hue scene...", items)
    if selected > -1:
        selectedId = index[selected]
        hSceneName = hueScenes[selectedId]['name']
        xbmc.log("[script.service.hue] In selectHueScene: selected: {}".format(selected))

    if selected > -1:
        return selectedId, hSceneName
    return None


def get_daylight(bridge):
    try:
        daylight = bridge.sensors['1']()['state']['daylight']
    except QhueException as exc:
        xbmc.log("[script.service.hue]: Get Daylight Qhue Exception: {}: {}".format(exc.type_id, exc.message))
        reporting.process_exception(exc)
        return
    return daylight


def activate(bridge, kgroups, ambiGroup=None):
    """
    Activates play action as appropriate for all groups. Used at sunset and when service is renabled via Actions.
    """
    xbmc.log("[script.service.hue] Activating scenes")

    for g in kgroups:
        try:
            if hasattr(g, 'kgroupID'):
                xbmc.log("[script.service.hue] in sunset() g: {}, kgroupID: {}".format(g, g.kgroupID))
                if ADDON.getSettingBool("group{}_enabled".format(g.kgroupID)):
                    g.activate()
        except AttributeError:
            pass

    if ADDON.getSettingBool("group3_enabled") and ambiGroup is not None:
        ambiGroup.activate()


def connect_bridge(monitor, silent=False):
    bridgeIP = ADDON.getSettingString("bridgeIP")
    bridgeUser = ADDON.getSettingString("bridgeUser")
    xbmc.log("[script.service.hue] in Connect() with settings: bridgeIP: {}, bridgeUser: {}".format(bridgeIP, bridgeUser))

    if bridgeIP and bridgeUser:
        if connection_test(bridgeIP):
            xbmc.log("[script.service.hue] in Connect(): Bridge responding to connection test.")
        else:
            xbmc.log("[script.service.hue] in Connect(): Bridge not responding to connection test, attempt finding a new bridge IP.")
            bridgeIP = discover_bridge_ip(monitor)
            if bridgeIP:
                xbmc.log("[script.service.hue] in Connect(): New IP found: {}. Saving".format(bridgeIP))
                ADDON.setSettingString("bridgeIP", bridgeIP)

        if bridgeIP:
            xbmc.log("[script.service.hue] in Connect(): Checking User")
            if user_test(bridgeIP, bridgeUser):
                bridge = qhue.Bridge(bridgeIP, bridgeUser, timeout=QHUE_TIMEOUT)
                settings_storage['connected'] = True
                xbmc.log("[script.service.hue] Successfully connected to Hue Bridge: {}".format(bridgeIP))
                if not silent:
                    notification(_("Hue Service"), _("Hue connected"), icon=xbmcgui.NOTIFICATION_INFO, sound=False)
                return bridge
        else:
            xbmc.log("[script.service.hue] Bridge not responding")
            notification(_("Hue Service"), _("Bridge connection failed"), icon=xbmcgui.NOTIFICATION_ERROR)
            settings_storage['connected'] = False
            return None

    else:
        xbmc.log("[script.service.hue] Bridge not configured")
        notification(_("Hue Service"), _("Bridge not configured"), icon=xbmcgui.NOTIFICATION_ERROR)
        settings_storage['connected'] = False
        return None


def get_light_gamut(bridge, light):
    try:
        gamut = bridge.lights()[light]['capabilities']['control']['colorgamuttype']
        # xbmc.log("[script.service.hue] Light: {}, gamut: {}".format(l, gamut))
    except QhueException:
        xbmc.log("[script.service.hue] Can't get gamut for light, defaulting to Gamut C: {}".format(light))
        return "C"
    if gamut == "A" or gamut == "B" or gamut == "C":
        return gamut
    return "C"  # default to C if unknown gamut type


def check_bridge_model(bridge):
    try:
        bridge_config = bridge.config()
        model = bridge_config["modelid"]
    except QhueException:
        xbmc.log("[script.service.hue] Exception: checkBridgeModel")
        return None
    if model == "BSB002":
        xbmc.log("[script.service.hue] Bridge model OK: {}".format(model))
        return True
    xbmc.log("[script.service.hue] Unsupported bridge model: {}".format(model))
    xbmcgui.Dialog().ok(_("Unsupported Hue Bridge"), _("Hue Bridge V1 (Round) is unsupported. Hue Bridge V2 (Square) is required."))
    return None


def notification(header, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=False):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def _perf_average(process_times):
    process_times = list(process_times)  # deque is mutating during iteration for some reason, so copy to list.
    size = len(process_times)
    total = 0
    if size > 0:
        for x in process_times:
            total += x
        average_process_time = int(total / size * 1000)
        return "{} ms".format(average_process_time)
    return _("Unknown")


def get_light_states(lights, bridge):
    states = {}

    for L in lights:
        try:
            states[L] = (bridge.lights[L]())
        except QhueException as exc:
            xbmc.log("[script.service.hue] Hue call fail: {}: {}".format(exc.type_id, exc.message))

    return states


class HueMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

    def onSettingsChanged(self):
        xbmc.log("[script.service.hue] Settings changed")
        read_settings()
        SETTINGS_CHANGED.set()

    def onNotification(self, sender, method, data):
        if sender == ADDONID:
            xbmc.log("[script.service.hue] Notification received: method: {}, data: {}".format(method, data))

            if method == "Other.disable":
                xbmc.log("[script.service.hue] Notification received: Disable")
                cache.set("script.service.hue.service_enabled", False)

            if method == "Other.enable":
                xbmc.log("[script.service.hue] Notification received: Enable")
                cache.set("script.service.hue.service_enabled", True)

            if method == "Other.actions":
                json_loads = json.loads(data)

                kgroupid = json_loads['group']
                action = json_loads['command']
                xbmc.log("[script.service.hue] Action Notification: group: {}, command: {}".format(kgroupid, action))
                cache.set("script.service.hue.action", (action, kgroupid), expiration=(timedelta(seconds=5)))
