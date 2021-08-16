import xbmc

from resources.lib import core, reporting


try:
    core.core()
except Exception as exc:
    xbmc.log("[script.service.hue][EXCEPTION] Core service exception: {}".format(exc))
    reporting.process_exception(exc)
