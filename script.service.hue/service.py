# -*- coding: utf-8 -*-
import xbmc

from resources.lib import core, ADDONVERSION, KODIVERSION
from resources.lib import reporting

try:
    core.core() #Run Hue service
except Exception as exc:
    xbmc.log("[script.service.hue] Core service exception")
    reporting.process_exception(exc)
