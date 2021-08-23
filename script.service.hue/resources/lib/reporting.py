import platform
import sys

import rollbar
import xbmcgui

from resources.lib.language import get_string as _
from . import ADDONVERSION, ROLLBAR_API_KEY, ADDONID, KODIVERSION, ADDONPATH


def process_exception(exc, level="critical"):
    if _error_report_requested(exc):
        _report_error(level)


def _error_report_requested(exc):
    return xbmcgui.Dialog().yesno(heading=f"{ADDONID} Error", message=_("The following error occurred:") + f"\n[COLOR=red]{exc}[/COLOR]\n" + _("Automatically report this error?"))


def _report_error(level="critical"):
    if "dev" in ADDONVERSION:
        env = "dev"
    else:
        env = "production"

    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip=False, code_version=ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser, bridgeIP', environment=env)
    rollbar.report_exc_info(sys.exc_info(), extra_data=data, level=level)
