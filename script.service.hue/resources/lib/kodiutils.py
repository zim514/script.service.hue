#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import datetime
import json
from json import JSONDecodeError

import xbmc
import xbmcgui

from . import ADDON, ADDONID, ADDONSETTINGS
from .language import get_string as _

cache_window = xbmcgui.Window(10000)


def validate_settings():
    _validate_schedule()
    _validate_ambilight()


def _validate_ambilight():
    xbmc.log(f"[script.service.hue] Validate ambilight config. Enabled: {ADDONSETTINGS.getBool('group3_enabled')}")
    if ADDONSETTINGS.getBool("group3_enabled"):
        light_ids = ADDONSETTINGS.getSetting("group3_Lights")
        if light_ids == "-1":
            ADDONSETTINGS.setBool("group3_enabled", False)
            xbmc.log("[script.service.hue] No ambilights selected")
            notification(_("Hue Service"), _("No lights selected for Ambilight."), icon=xbmcgui.NOTIFICATION_ERROR)


def _validate_schedule():
    xbmc.log(f"[script.service.hue] Validate schedule. Schedule Enabled: {ADDONSETTINGS.getBool('enableSchedule')}")
    if ADDONSETTINGS.getBool("enableSchedule"):
        try:
            convert_time(ADDONSETTINGS.getString("startTime"))
            convert_time(ADDONSETTINGS.getString("endTime"))
            # xbmc.log("[script.service.hue] Time looks valid")
        except ValueError as e:
            ADDONSETTINGS.setBool("EnableSchedule", False)
            xbmc.log(f"[script.service.hue] Invalid time settings: {e}")
            notification(_("Hue Service"), _("Invalid start or end time, schedule disabled"), icon=xbmcgui.NOTIFICATION_ERROR)


def convert_time(time):
    hour = int(time.split(":")[0])
    minute = int(time.split(":")[1])
    return datetime.time(hour, minute)


def notification(header, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=False):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def cache_get(key: str):
    data_str = cache_window.getProperty(f"{ADDONID}.{key}]")

    try:
        data = json.loads(data_str)
        #xbmc.log(f"[script.service.hue] Cache Get: {key}, {data}")
        return data
    except JSONDecodeError:
        # Occurs when Cache is empty or unreadable (Eg. Old SimpleCache data still in memory because Kodi hasn't restarted)
        # xbmc.log(f"[script.service.hue] cache_get JSONDecodeError: {key}: {data_str}")
        return None


def cache_set(key: str, data):
    data_str = json.dumps(data)
    # xbmc.log(f"[script.service.hue] Cache Set: {key}, {data_str} - {data_type}")
    cache_window.setProperty(f"{ADDONID}.{key}]", data_str)
    return
