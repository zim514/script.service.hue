import os

TESTING_ENV = False

try:
    import xbmc
    import xbmcaddon

    __addon__ = xbmcaddon.Addon()
    __cwd__ = __addon__.getAddonInfo('path')
    __icon__ = os.path.join(__cwd__, "icon.png")
    __settings__ = os.path.join(__cwd__, "resources", "settings.xml")
    __xml__ = os.path.join(__cwd__, 'addon.xml')
except ImportError:
    TESTING_ENV = True


def xbmclog(message):
    if TESTING_ENV:
        pass
    else:
        xbmc.log(message)


def notify(title, msg=''):
    if TESTING_ENV:
        pass
    else:
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
