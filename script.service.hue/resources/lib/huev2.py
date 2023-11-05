#      Copyright (C) 2023 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import requests
import simplejson as json

import xbmc
import xbmcgui

from .kodiutils import notification
from .language import get_string as _


class HueAPIv2(object):
    def __init__(self, ip=None, key=None, discover=False):
        self.session = requests.Session()
        self.session.verify = False
        # session.headers.update({'hue-application-key': hue_application_key})

        self.connected = False
        self.retries = 0
        self.max_retries = 5
        self.max_timeout = 5
        self.ip = ip
        self.key = key
        self.base_url = None

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

        devices = self.get("device")
        device_id = self.get_device_by_archetype(devices, 'bridge_v2')
        software_version = self.get_attribute_value(devices, device_id, ['product_data', 'software_version'])
        # Check that software_version is at least 1.60, by properly parsing it as a version number

        api_split = software_version.split(".")

        if software_version and int(api_split[0]) >= 1 and int(api_split[1]) >= 38:  # minimum bridge version 1.38
            xbmc.log(f"[script.service.hue] v2 connect() software version: {software_version}")
            return True

        notification(_("Hue Service"), _("Bridge outdated. Please update your bridge."), icon=xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"[script.service.hue] v2 connect():  Connected! Bridge API too old: {software_version}")
        return False

        xbmc.log(f"[script.service.hue] v2 connect() software version: {software_version}")

    def discover(self):
        pass

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
            raise

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

    def search_dict(self, d, key):
        if key in d:
            return d[key]
        for k, v in d.items():
            if isinstance(v, dict):
                item = self.search_dict(v, key)
                if item is not None:
                    return item
            elif isinstance(v, list):
                for d in v:
                    if isinstance(d, dict):
                        item = self.search_dict(d, key)
                        if item is not None:
                            return item
