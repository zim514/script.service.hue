import xbmc

from resources.lib import core
from resources.lib import reporting

try:
    core.core() #Run Hue service
except Exception as exc:
    xbmc.log("[script.service.hue] Core service exception")
    reporting.process_exception(exc)
