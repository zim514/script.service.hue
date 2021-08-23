import xbmc

from resources.lib import core, reporting


try:
    core.core()
except Exception as exc:
    xbmc.log(f"[script.service.hue][EXCEPTION] Core service exception: {exc}")
    reporting.process_exception(exc)
