# -*- coding: utf-8 -*-

import logging

import xbmcaddon

from resources.lib import kodilogging
from resources.lib import service


# Keep this file to a minimum, as Kodi
# doesn't keep a compiled copy of this
ADDON = xbmcaddon.Addon()
kodilogging.config()

service.run()


