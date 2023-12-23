#      Copyright (C) 2023 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.
import threading

import requests
import urllib3

import simplejson as json
from simplejson import JSONDecodeError
import datetime

import xbmc
import xbmcgui
from . import ADDON, reporting, ADDONSETTINGS

from .kodiutils import notification
from .language import get_string as _


class HueAPIv2(object):
    def __init__(self, monitor, ip=None, key=None, discover=False):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Old hue bridges use insecure https

        self.session = requests.Session()
        self.session.verify = False
        # session.headers.update({'hue-application-key': hue_application_key})

        self.connected = False
        self.devices = None
        self.bridge_id = None
        self.retries = 0
        self.max_retries = 5
        self.max_timeout = 5
        self.ip = ip
        self.key = key
        self.base_url = None
        self.sunset = None
        self.monitor = monitor

        if ip is not None and key is not None:
            self.connected = self.connect()
        elif self.discover:
            self.discover()
        else:
            raise ValueError("ip and key must be provided or discover must be True")

    def connect(self):
        xbmc.log(f"[script.service.hue] v2 connect() ip: {self.ip}, key: {self.key}")
        self.base_url = f"https://{self.ip}/clip/v2/resource/"
        self.session.headers.update({'hue-application-key': self.key})

        self.devices = self.get("device")
        self.bridge_id = self.get_device_by_archetype(self.devices, 'bridge_v2')

        if self._check_version():
            self.connected = True
            self.update_sunset()
            return True
        else:
            self.connected = False
            return False

    def reconnect(self):
        xbmc.log(f"[script.service.hue] v2 reconnect() with settings: bridgeIP: {self.ip}, bridgeUser: {self.key}")
        retries = 0

        while retries < 11 and not self.monitor.abortRequested():
            if self._check_version():
                xbmc.log(f"[script.service.hue] reconnect(): Check version successful! ")
                notification(_("Hue Service"), _("Reconnected"))
                return True
            else:
                if self._discover_bridge_ip():
                    xbmc.log(f"[script.service.hue] v2 reconnect(): New IP found: {self.bridge_ip}. Saving")
                    if self._check_version():
                        xbmc.log(f"[script.service.hue] in reconnect(): Version check successful. Saving bridge IP")
                        ADDON.setSettingString("bridgeIP", self.bridge_ip)
                        return True
                else:
                    xbmc.log(f"[script.service.hue] Bridge not found. Attempt {retries}/10. Trying again in 2 minutes.")
                    notification(_("Hue Service"), _("Connection lost. Trying again in 2 minutes"))

            retries = retries + 1
            self.monitor.waitForAbort(120)  # Retry in 2 minutes

        # give up
        xbmc.log(f"[script.service.hue] v2 reconnect(). Attempt: {retries}/10. Shutting down")
        notification(_("Hue Service"), _("Connection lost. Check settings. Shutting down"))
        self.connected = False
        return False

    def discover(self):
        xbmc.log("[script.service.hue] v2 Start discover")
        # Create new config if none exists. Returns success or fail as bool
        ADDON.setSettingString("bridgeIP", "")
        ADDON.setSettingString("bridgeUser", "")
        self.bridge_ip = ""
        self.bridge_user = ""

        self.connected = False

        progress_bar = xbmcgui.DialogProgress()
        progress_bar.create(_('Searching for bridge...'))
        progress_bar.update(5, _("Discovery started"))

        complete = False
        while not progress_bar.iscanceled() and not complete and not self.monitor.abortRequested():

            progress_bar.update(percent=10, message=_("N-UPnP discovery..."))
            bridge_ip_found = self._discover_nupnp()

            if not bridge_ip_found and not progress_bar.iscanceled():
                manual_entry = xbmcgui.Dialog().yesno(_("Bridge not found"),
                                                      _("Bridge not found automatically. Please make sure your bridge is up to date and has access to the internet. [CR]Would you like to enter your bridge IP manually?")
                                                      )
                if manual_entry:
                    self.bridge_ip = xbmcgui.Dialog().numeric(3, _("Bridge IP"))

            if self.bridge_ip:
                progress_bar.update(percent=50, message=_("Connecting..."))
                if self._check_version() and not progress_bar.iscanceled():
                    progress_bar.update(percent=100, message=_("Found bridge: ") + self.bridge_ip)
                    self.monitor.waitForAbort(1)

                    bridge_user_created = self._create_user(progress_bar)

                    if bridge_user_created:
                        xbmc.log(f"[script.service.hue] User created: {self.bridge_user}")
                        progress_bar.update(percent=90, message=_("User Found![CR]Saving settings..."))

                        ADDON.setSettingString("bridgeIP", self.bridge_ip)
                        ADDON.setSettingString("bridgeUser", self.bridge_user)

                        progress_bar.update(percent=100, message=_("Complete!"))
                        self.monitor.waitForAbort(5)
                        progress_bar.close()
                        xbmc.log("[script.service.hue] Bridge discovery complete")
                        self.connect()
                        return True

                    elif progress_bar.iscanceled():
                        xbmc.log("[script.service.hue] Cancelled 2")
                        progress_bar.update(percent=100, message=_("Cancelled"))
                        progress_bar.close()

                    else:
                        xbmc.log(f"[script.service.hue] User not created, received: {self.bridge_user}")
                        progress_bar.update(percent=100, message=_("User not found[CR]Check your bridge and network."))
                        self.monitor.waitForAbort(5)
                        progress_bar.close()
                        return
                elif progress_bar.iscanceled():
                    xbmc.log("[script.service.hue] Cancelled 3")

                    progress_bar.update(percent=100, message=_("Cancelled"))
                    progress_bar.close()
                else:
                    progress_bar.update(percent=100, message=_("Bridge not found[CR]Check your bridge and network."))
                    xbmc.log("[script.service.hue] Bridge not found, check your bridge and network")
                    self.monitor.waitForAbort(5)
                    progress_bar.close()

            xbmc.log("[script.service.hue] Cancelled 4")
            complete = True
            progress_bar.update(percent=100, message=_("Cancelled"))
            progress_bar.close()

        if progress_bar.iscanceled():
            xbmc.log("[script.service.hue] Bridge discovery cancelled by user 5")
            progress_bar.update(percent=100, message=_("Cancelled"))
            progress_bar.close()

    def _check_version(self):
        try:
            software_version = self.get_attribute_value(self.devices, self.bridge_id,
                                                        ['product_data', 'software_version']
                                                        )
            api_split = software_version.split(".")
        except KeyError as error:
            notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."),
                         icon=xbmcgui.NOTIFICATION_ERROR
                         )
            xbmc.log(
                f"[script.service.hue] in _version_check():  Connected! Bridge too old: {software_version}, error: {error}"
            )
            return False
        except Exception as exc:
            reporting.process_exception(exc)
            return False

        if int(api_split[0]) >= 1 and int(api_split[1]) >= 60:  # minimum bridge version 1.60
            xbmc.log(f"[script.service.hue] v2 connect() software version: {software_version}")
            return True

        notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."),
                     icon=xbmcgui.NOTIFICATION_ERROR
                     )
        xbmc.log(f"[script.service.hue] v2 connect():  Connected! Bridge API too old: {software_version}")
        return False

    def update_sunset(self):
        geolocation = self.get("geolocation")  # TODO: Support cases where geolocation is not configured on bridge.
        xbmc.log(f"[script.service.hue] v2 update_sunset(): geolocation: {geolocation}")
        sunset_str = self.search_dict(geolocation, "sunset_time")
        self.sunset = datetime.datetime.strptime(sunset_str, '%H:%M:%S').time()
        xbmc.log(f"[script.service.hue] v2 update_sunset(): sunset: {self.sunset}")

    def get(self, resource):
        url = f"{self.base_url}/{resource}"

        try:
            response = self.session.get(url)

            if response.status_code == 200:
                try:
                    data = json.loads(response.text)
                    return data
                except json.JSONDecodeError as x:
                    xbmc.log(f"[script.service.hue] v2 get() JSONDecodeError: {x}")
                    raise

            elif response.status_code in [401, 403]:
                xbmc.log(f"[script.service.hue] v2 get() Auth error: {response.status_code}")
                raise requests.RequestException
            elif response.status_code in [500, 502, 503, 504]:
                xbmc.log(f"[script.service.hue] v2 get() Server error: {response.status_code}")
                raise requests.RequestException
            elif response.status_code in [400, 404]:
                xbmc.log(f"[script.service.hue] v2 get() Client error: {response.status_code}")
                raise requests.RequestException
            elif response.status_code == 429:
                xbmc.log(f"[script.service.hue] v2 get() Too many requests: {response.status_code}")
                raise requests.RequestException

        except requests.RequestException as x:
            xbmc.log(f"[script.service.hue] v2 get() RequestException: {x}")
            self.connected = False

    def get_scenes(self):
        scenes_data = self.get("scene")
        rooms_data = self.get("room")
        zones_data = self.get("zone")

        # xbmc.log(f"[script.service.hue] v2 get_scenes(): scenes: {scenes_json}")

        rooms_dict = {room['id']: room['metadata']['name'] for room in rooms_data['data']}
        zones_dict = {zone['id']: zone['metadata']['name'] for zone in zones_data['data']}

        # xbmc.log(f"[script.service.hue] v2 get_scenes(): room_dict: {rooms_dict}")
        # xbmc.log(f"[script.service.hue] v2 get_scenes(): zones_dict: {zones_dict}")
        scenes_dict = {}

        for scene in scenes_data['data']:
            scene_id = scene['id']
            scene_name = scene['metadata']['name']
            room_id = scene['group']['rid']
            room_name = rooms_dict.get(room_id)
            # If not found in room_dict, try to get it from zones_dict
            if room_name is None:
                room_name = zones_dict.get(room_id, _("Unknown Area"))

            scenes_dict[scene_id] = {'scene_name': scene_name, 'room_name': room_name}

        dict_items = "\n".join([f"{key}: {value}" for key, value in scenes_dict.items()])
        xbmc.log(f"[script.service.hue] v2 get_scenes(): scenes_dict: {dict_items}")

        return scenes_dict

    def configure_scene(self, group_id, action):
        scene = self.select_hue_scene()
        xbmc.log(f"[script.service.hue] v2 selected scene: {scene}")
        if scene is not None:
            # setting ID format example: group0_startSceneID
            ADDONSETTINGS.setString(f"group{group_id}_{action}SceneID", scene[0])
            ADDONSETTINGS.setString(f"group{group_id}_{action}SceneName", scene[1])
            ADDON.openSettings()

    def select_hue_scene(self):

        h_scene_name = ""
        xbmc.log("[script.service.hue] In selectHueScene{}")

        hue_scenes = self.get_scenes()

        items = []
        index = []
        selected_id = -1

        for scene in hue_scenes:
            xbmc.log(f"[script.service.hue] In selectHueScene: scene: {scene}")

            h_scene_name = hue_scenes[scene]['scene_name']
            h_room_name = hue_scenes[scene]['room_name']

            index.append(scene)
            items.append(xbmcgui.ListItem(label=h_scene_name, label2=h_room_name))

        selected = xbmcgui.Dialog().select("Select Hue scene...", items, useDetails=True)
        if selected > -1:
            selected_id = index[selected]
            selected_scene_name = hue_scenes[selected_id]['scene_name']
            selected_room_name = hue_scenes[selected_id]['room_name']
            selected_name = f"{selected_scene_name} - {selected_room_name}"
            xbmc.log(f"[script.service.hue] In selectHueScene: selected: {selected}")
            return selected_id, selected_name
        return None

    def _discover_bridge_ip(self):
        # discover hue bridge IP silently for non-interactive discovery / bridge IP change.
        xbmc.log("[script.service.hue] In discoverBridgeIP")
        if self._discover_nupnp():
            xbmc.log(f"[script.service.hue] In discoverBridgeIP, discover_nupnp SUCCESS: {self.bridge_ip}")
            if self._check_version():
                xbmc.log(f"[script.service.hue] In discoverBridgeIP, check version SUCCESS")
                return True
        xbmc.log(f"[script.service.hue] In discoverBridgeIP, discover_nupnp FAIL: {self.bridge_ip}")
        return False

    def _discover_nupnp(self):
        xbmc.log("[script.service.hue] v2: In kodiHue discover_nupnp()")
        req = ""
        try:
            req = requests.get('https://discovery.meethue.com/')
            if req.status_code == 429:
                return None
            result = req.json()
        except requests.RequestException as error:
            xbmc.log(f"[script.service.hue] Nupnp failed: {error}")
            return None
        except (JSONDecodeError, json.JSONDecodeError) as error:  # when discovery.meethue.com returns empty JSON or 429
            xbmc.log(f"[script.service.hue] Nupnp failed: {error}, req: {req}")
            return None

        bridge_ip = None
        if result:
            try:
                bridge_ip = result[0]["internalipaddress"]
            except KeyError:
                xbmc.log("[script.service.hue] Nupnp: No IP found in response")
                return None
        self.bridge_ip = bridge_ip
        return True

    @staticmethod
    def get_device_by_archetype(json_data, archetype):
        for device in json_data['data']:
            if device['product_data']['product_archetype'] == archetype:
                return device['id']
        return None

    @staticmethod
    def get_attribute_value(json_data, device_id, attribute_path):
        for device in json_data['data']:
            if device['id'] == device_id:
                value = device
                for key in attribute_path:
                    value = value.get(key)
                    if value is None:
                        return None
                return value
        return None

    @staticmethod
    def search_dict(d, key):
        if key in d:
            return d[key]
        for k, v in d.items():
            if isinstance(v, dict):
                item = HueAPIv2.search_dict(v, key)
                if item is not None:
                    return item
            elif isinstance(v, list):
                for d in v:
                    if isinstance(d, dict):
                        item = HueAPIv2.search_dict(d, key)
                        if item is not None:
                            return item
