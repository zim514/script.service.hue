import xbmc

from resources.lib import menu, reporting

try:
    menu.menu()
except Exception as exc:
    xbmc.log("[script.service.hue][EXCEPTION] Command exception: {}".format(exc))
    reporting.process_exception(exc)
