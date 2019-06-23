# -*- coding: utf-8 -*-

import logging
from builtins import str

from kodi_six import xbmc, xbmcgui
#import xbmcgui

from . import globals



def notification(header, message, time=5000, icon=globals.ADDON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def show_settings():
    globals.ADDON.openSettings()


def get_setting(setting):
    return globals.ADDON.getSetting(setting).strip()


def set_setting(setting, value):
    globals.ADDON.setSetting(setting, str(value))


def get_setting_as_bool(setting):
    return get_setting(setting).lower() == "true"


def get_setting_as_float(setting):
    try:
        return float(get_setting(setting))
    except ValueError:
        return 0


def get_setting_as_int(setting):
    try:
        return int(get_setting_as_float(setting))
    except ValueError:
        return 0


def get_string(string_id):
    return globals.ADDON.getLocalizedString(string_id)

