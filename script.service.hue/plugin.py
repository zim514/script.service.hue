# -*- coding: utf-8 -*-
import xbmc

from resources.lib import menu, reporting

try:
    menu.menu()  # Run menu
except Exception as exc:
    xbmc.log("[script.service.hue] Command exception")
    reporting.process_exception(exc)

