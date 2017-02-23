import os

import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__icon__ = os.path.join(__cwd__, "icon.png")
__settings__ = os.path.join(__cwd__, "resources", "settings.xml")
__xml__ = os.path.join(__cwd__, 'addon.xml')

API_KEY = "7OOEGRV8Y2SVNTS29EBJ"
API_SEARCH_URL = "http://www.chapterdb.org/chapters/search"
XML_NAMESPACE = "http://jvance.com/2008/ChapterGrabber"
THRESHOLD_LAST_CHAPTER = 60


def notify(title, msg=''):
    xbmc.executebuiltin('XBMC.Notification({}, {}, 3, {})'.format(
        title, msg, __icon__))


def get_version():
    # prob not the best way...
    global __xml__
    try:
        for line in open(__xml__):
            if line.find("ambilight") != -1 and line.find("version") != -1:
                return line[line.find("version=")+9:line.find(" provider")-1]
    except:
        return "unknown"
