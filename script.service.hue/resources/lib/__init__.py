"""Global constants, threading events, and addon metadata for the Hue service.

Attributes:
    STRDEBUG (bool): When True, display string IDs instead of translations in the UI.
    FORCEDEBUGLOG (bool): Force debug-level logs to output at WARNING level.
    TIMEOUT (int): Default HTTP request timeout in seconds.
    MAX_RETRIES (int): Maximum number of retry attempts for API requests.
    NOTIFICATION_THRESHOLD (int): Retry count at which to show a user notification.
    MINIMUM_COLOR_DISTANCE (float): Minimum CIE xy distance to trigger a light update.
    BRIDGE_SETTINGS_CHANGED (Event): Signals the main loop to reconnect the bridge.
    AMBI_RUNNING (Event): Signals whether the ambilight capture loop is active.
    PROCESS_TIMES (deque): Rolling buffer of recent frame processing times (seconds).
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import functools
import time
from collections import deque
from threading import Event

import xbmc
import xbmcaddon
import xbmcvfs

STRDEBUG = False  # Show string ID in UI
FORCEDEBUGLOG = False # Force output of debug logs regardless of Kodi logging setting
TIMEOUT = 1 # requests default timeout
MAX_RETRIES = 7
NOTIFICATION_THRESHOLD = 2
MINIMUM_COLOR_DISTANCE = 0.005
BRIDGE_SETTINGS_CHANGED = Event()
AMBI_RUNNING = Event()
PROCESS_TIMES = deque(maxlen=100)
ROLLBAR_API_KEY = "48f832ef0f3947c9a8443a36b94bcfbd"

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
# ADDONDIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ADDONPATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
ADDONVERSION = ADDON.getAddonInfo('version')
KODIVERSION = xbmc.getInfoLabel('System.BuildVersion')


def timer(func):
    """Decorator that records the runtime of the wrapped function.

    Appends the elapsed time (in seconds) to the global :data:`PROCESS_TIMES`
    deque, which is used to compute average frame processing time for ambilight.
    """

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.time()  # 1
        value = func(*args, **kwargs)
        end_time = time.time()  # 2
        run_time = end_time - start_time  # 3
        PROCESS_TIMES.append(run_time)
        return value

    return wrapper_timer
