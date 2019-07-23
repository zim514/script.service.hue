# -*- coding: utf-8 -*-


import datetime

#from kodi_six import xbmcgui
import xbmcgui


from . import globals


def notification(header, message, time=5000, icon=globals.ADDON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def convertTime(time):
    hour=int(time.split(":")[0])
    minute=int(time.split(":")[1])
    return datetime.time(hour,minute)
