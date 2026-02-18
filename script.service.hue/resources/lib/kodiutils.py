"""Kodi helper utilities for logging, notifications, time conversion, and window-property caching.

Provides a lightweight inter-process communication mechanism via Kodi window
properties (Home window 10000), used to share state between the service and
plugin entry points.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import datetime
import json
from json import JSONDecodeError

import xbmcgui
import xbmc

from . import ADDON, ADDONID, FORCEDEBUGLOG

cache_window = xbmcgui.Window(10000)


def notification(header, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=False):
    """Display a Kodi notification popup.

    Args:
        header: Notification title.
        message: Notification body text.
        time: Display duration in milliseconds.
        icon: Path to notification icon or a built-in icon constant.
        sound: Whether to play a notification sound.
    """
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def convert_time(time_string: str) -> datetime.time:
    """Parse a time string in ``HH:MM`` or ``HH:MM:SS`` format into a :class:`datetime.time`.

    Args:
        time_string: Time string with colon-separated components.

    Returns:
        Parsed time object.
    """
    parts = list(map(int, time_string.split(':')))
    if len(parts) == 2:
        return datetime.time(parts[0], parts[1])
    elif len(parts) == 3:
        return datetime.time(parts[0], parts[1], parts[2])


def cache_get(key: str):
    """Retrieve a JSON-serialized value from the Kodi window-property cache.

    Args:
        key: Cache key (automatically prefixed with the addon ID).

    Returns:
        Deserialized Python object, or ``None`` if the key is missing or invalid.
    """
    data_str = cache_window.getProperty(f"{ADDONID}.{key}")
    try:
        data = json.loads(data_str)
        return data
    except JSONDecodeError:
        return None


def cache_set(key: str, data):
    """Store a JSON-serializable value in the Kodi window-property cache.

    Args:
        key: Cache key (automatically prefixed with the addon ID).
        data: Any JSON-serializable Python object.
    """
    data_str = json.dumps(data)
    cache_window.setProperty(f"{ADDONID}.{key}", data_str)
    return


def log(message, level=xbmc.LOGDEBUG):
    """Write a message to the Kodi log.

    When :data:`FORCEDEBUGLOG` is ``True``, all messages are elevated to
    ``LOGWARNING`` so they appear regardless of Kodi's log level setting.

    Args:
        message: Log message string.
        level: Kodi log level constant (default ``LOGDEBUG``).
    """
    if FORCEDEBUGLOG:
        xbmc.log(message, xbmc.LOGWARNING)
    else:
        xbmc.log(message, level)
