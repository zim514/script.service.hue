# -*- coding: utf-8 -*-

import logging

import xbmcgui
import xbmc
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


from . import globals


# read settings

def configLog():


    global setting_LogLevel
    global setting_SeparateLogFile
     
    setting_LogLevel = int(globals.ADDON.getSetting("logLevel"))
    setting_SeparateLogFile = int(globals.ADDON.getSetting("separateLogFile"))

    __addonworkdir__ = xbmc.translatePath(globals.ADDON.getAddonInfo('profile').decode('utf-8'))
    
    formatter = logging.Formatter(b'[{}][%(funcName)s] %(filename)s(%(lineno)d): %(message)s\n'.format(globals.ADDONID))
    kodilogger = logging.getLogger(globals.ADDONID)
    kodilogger.setFormatter(formatter)
    
    
    # prepare datadir
    # directory and file is local to the filesystem
    # no need to use xbmcvfs
    if not os.path.isdir(__addonworkdir__):
        xbmc.log("Hue: profile directory doesn't exist: " + __addonworkdir__.encode('utf-8') + "   Trying to create.", level=xbmc.LOGNOTICE)
        try:
            os.mkdir(__addonworkdir__)
            xbmc.log("Hue: profile directory created: " + __addonworkdir__.encode('utf-8'), level=xbmc.LOGNOTICE)
        except OSError as e:
            xbmc.log("Hue: Log: can't create directory: " + __addonworkdir__.encode('utf-8'), level=xbmc.LOGERROR)
            xbmc.log("Exception: " + str(e.message).encode('utf-8'), xbmc.LOGERROR)
     
    # prepare external log handler
    # https://docs.python.org/2/library/logging.handlers.html
    global filelogger
    filelogger = logging.getLogger(__name__)
    loghandler = logging.handlers.TimedRotatingFileHandler(os.path.join(__addonworkdir__, 'kodiHue.log',), when="midnight", interval=1, backupCount=2)
    
    rootlogger = logging.getLogger()
    
    filelogger.addHandler(loghandler)
    formatter = logging.Formatter(b'[{}][%(funcName)s] %(filename)s(%(lineno)d): %(message)s\n'.format(globals.ADDONID))
    pass
    #filelogger.setFormatter(formatter)

    
    
    # xbmc loglevels: https://forum.kodi.tv/showthread.php?tid=324570&pid=2671926#pid2671926
    # 0 = LOGDEBUG
    # 1 = LOGINFO
    # 2 = LOGNOTICE
    # 3 = LOGWARNING
    # 4 = LOGERROR
    # 5 = LOGSEVERE
    # 6 = LOGFATAL
    # 7 = LOGNONE

def log(message, severity=xbmc.LOGDEBUG):
    """Log message to internal Kodi log or external log file.

    Arguments:
        message {str} -- message text

    Keyword Arguments:
        severity {int} -- log level (default: {xbmc.LOGDEBUG})
    """

    # get log level settings
    setting_LogLevel = int(globals.ADDON.getSetting("logLevel"))
    setting_SeparateLogFile = int(globals.ADDON.getSetting("separateLogFile"))

    if severity >= setting_LogLevel:
        # log the message to Log
        if setting_SeparateLogFile == 0:
            # use kodi.log for logging
            # check if string is str
            if isinstance(message, str):
                # convert to unicode string
                message = message.decode('utf-8')
            # re-encode to utf-8
            xbmc.log("[SCRIPT.SERVICE.HUE]: " + message.encode('utf-8'), level=xbmc.LOGNONE)
        else:
            # use smangler's own log file located in addon's datadir
            # construct log text
            # cut last 3 trailing zero's from timestamp
            logtext = str(datetime.now)[:-3]
            if severity == xbmc.LOGDEBUG:
                logtext += "   DEBUG: "
            elif severity == xbmc.LOGINFO:
                logtext += "    INFO: "
            elif severity == xbmc.LOGNOTICE:
                logtext += "  NOTICE: "
            elif severity == xbmc.LOGWARNING:
                logtext += " WARNING: "
            elif severity == xbmc.LOGERROR:
                logtext += "   ERROR: "
            elif severity == xbmc.LOGSEVERE:
                logtext += "  SEVERE: "
            elif severity == xbmc.LOGFATAL:
                logtext += "   FATAL: "
            else:
                logtext += "    NONE: "
            logtext += message
            # append line to external log file
            # logging via warning level to prevent filtering of messages by default filtering level of ROOT logger
            filelogger.warning(logtext)



def notification(header, message, time=5000, icon=globals.ADDON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def show_settings():
    globals.ADDON.openSettings()


def get_setting(setting):
    return globals.ADDON.getSetting(setting).strip().decode('utf-8')


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
    return globals.ADDON.getLocalizedString(string_id).encode('utf-8', 'ignore')

