# -*- coding: utf-8 -*-
import xbmc

from resources.lib import menu, ADDONVERSION, KODIVERSION,reporting



try:
    menu.menu()  # Run menu
except Exception as exc:
    xbmc.log("Command exception")
    reporting.process_exception(exc)

