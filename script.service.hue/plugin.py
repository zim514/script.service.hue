"""Plugin UI entry point for the Kodi Hue addon.

Instantiates :class:`resources.lib.menu.Menu` which renders the user-facing
navigation menus and handles toggle/action commands. Uncaught exceptions are
forwarded to Rollbar via :mod:`resources.lib.reporting`.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

from resources.lib import menu, reporting

try:
    menu.Menu()
except Exception as exc:
    reporting.process_exception(exc)
