from . import ADDON
from . import cache

settings_storage = {'disable_connection_message': False
                    }


def update_settings_cache():
    settings_storage['disable_connection_message'] = ADDON.getSettingBool("disableConnectionMessage")

    cache.set("script.service.hue.settings", settings_storage)
