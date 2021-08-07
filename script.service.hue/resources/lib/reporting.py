import platform
import sys

import rollbar
import xbmcgui

from resources.lib.language import get_string as _
from . import ADDONVERSION, ROLLBAR_API_KEY, ADDONID, KODIVERSION, ADDONPATH


def error_report_requested(exc):
    return xbmcgui.Dialog().yesno(heading="{} {}".format(ADDONID, _("Error")), message=_("The following error occurred:") +
                                                                                       "\n[COLOR=red]{}[/COLOR]\n".format(exc) +
                                                                                       _("Automatically report this error?")
                                  )


def report_error(url=None):
    data = {
        'machine': platform.machine(),
        'platform': platform.system(),
        'kodi': KODIVERSION,
        'url': url,
    }
    rollbar.init(ROLLBAR_API_KEY, capture_ip="anonymize", code_version=ADDONVERSION, root=ADDONPATH, scrub_fields='bridgeUser')
    rollbar.report_exc_info(sys.exc_info(), extra_data=data)


def process_exception(exc):
    if error_report_requested(exc):
        report_error()
