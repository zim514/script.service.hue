"""Persistent background service entry point for the Kodi Hue addon.

Delegates to :func:`resources.lib.core.core_dispatcher` which either handles
a RunScript command (discover, sceneSelect, ambiLightSelect) from addon
settings or starts the main service loop. Uncaught exceptions are forwarded
to Rollbar via :mod:`resources.lib.reporting`.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

from resources.lib import core, reporting

try:
    core.core_dispatcher()
except Exception as exc:
    reporting.process_exception(exc)
