"""Error reporting via Rollbar with user consent and sensitive data scrubbing.

Provides a three-step error handling flow:
1. Log the exception locally.
2. Prompt the user for consent to report.
3. Submit to Rollbar with bridge credentials scrubbed.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import platform
import sys
import traceback

import rollbar
import xbmcgui

from . import ADDONVERSION, ROLLBAR_API_KEY, KODIVERSION, ADDONPATH, ADDON
from .language import get_string as _
from .kodiutils import log


def process_exception(exc, level="critical", error="", logging=False):
    """Log an exception and optionally report it to Rollbar (with user consent).

    Args:
        exc: The exception instance or descriptive string.
        level: Rollbar severity level (``"critical"``, ``"error"``, ``"warning"``).
        error: Additional context string appended to the report.
        logging: If ``True``, send as a message rather than an exc_info report.
    """
    log(f"[SCRIPT.SERVICE.HUE] *** EXCEPTION ***:  Type: {type(exc)},\n Exception: {exc},\n Error: {error},\n Traceback: {traceback.format_exc()}")
    if ADDON.getSettingBool("error_reporting"):
        if _error_report_dialog(exc):
            _report_error(level, error, exc, logging)

'''
    if exc is RequestException:
        log("[SCRIPT.SERVICE.HUE] RequestException, not reporting to rollbar")
        notification(_("Hue Service"), _("Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
    else:
'''


def _error_report_dialog(exc):
    """Show a yes/no/custom dialog asking the user whether to report the error.

    Returns:
        ``True`` if the user chose "Yes", ``False`` otherwise. Selecting
        "Never report errors" also disables future prompts.
    """
    response = xbmcgui.Dialog().yesnocustom(heading=_("Hue Service Error"), message=_("The following error occurred:") + f"\n[COLOR=red]{exc}[/COLOR]\n" + _("Automatically report this error?"), customlabel=_("Never report errors"))
    if response == 2:
        log("[SCRIPT.SERVICE.HUE] Error Reporting disabled")
        ADDON.setSettingBool("error_reporting", False)
        return False
    return response


def _report_error(level="critical", error="", exc="", logging=False):
    """Submit the error to Rollbar.

    Automatically determines the environment (``"dev"`` vs ``"production"``)
    based on the addon version string. Sensitive fields (bridge IP, user key)
    are scrubbed before transmission.

    Args:
        level: Rollbar severity level.
        error: Additional context string.
        exc: The exception instance or message.
        logging: If ``True``, use ``report_message`` instead of ``report_exc_info``.
    """
    if any(val in ADDONVERSION for val in ["dev", "alpha", "beta"]):
        env = "dev"
    else:
        env = "production"

    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
        'error': error,
        'exc': traceback.format_exc()
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip=False, code_version="v" + ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser, bridgeIP, bridge_user, bridge_ip, server.host', environment=env, handler="thread")
    if logging:
        rollbar.report_message(exc, extra_data=data, level=level)
    else:
        rollbar.report_exc_info(sys.exc_info(), extra_data=data, level=level)
