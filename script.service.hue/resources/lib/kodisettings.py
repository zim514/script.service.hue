from datetime import datetime

import xbmcgui
import simplecache

from resources.lib import logger, ADDON
from resources.lib.language import get_string as _

cache = simplecache.SimpleCache()
settings_storage = {}


def validate_schedule():
    logger.debug("Validate schedule. Schedule Enabled: {}".format(settings_storage['enableSchedule']))
    if settings_storage['enableSchedule']:
        try:
            convert_time(settings_storage['startTime'])
            convert_time(settings_storage['endTime'])
            logger.debug("Time looks valid")
        except ValueError as e:
            logger.error("Invalid time settings: {}".format(e))

            xbmcgui.Dialog().notification(_("Hue Service"), _("Invalid start or end time, schedule disabled"), icon=xbmcgui.NOTIFICATION_ERROR)
            ADDON.setSettingBool("EnableSchedule", False)
            settings_storage['enableSchedule'] = False


def read_settings():
    settings_storage['disable_connection_message'] = ADDON.getSettingBool("disableConnectionMessage")
    settings_storage['reloadFlash'] = ADDON.getSettingBool("reloadFlash")
    settings_storage['initialFlash'] = ADDON.getSettingBool("initialFlash")
    settings_storage['forceOnSunset'] = ADDON.getSettingBool("forceOnSunset")
    settings_storage['daylightDisable'] = ADDON.getSettingBool("daylightDisable")
    cache.set("script.service.hue.daylightDisable", ADDON.getSettingBool("daylightDisable"))

    settings_storage['enableSchedule'] = ADDON.getSettingBool("enableSchedule")
    settings_storage['startTime'] = ADDON.getSetting("startTime")  # string HH:MM
    settings_storage['endTime'] = ADDON.getSetting("endTime")  # string HH:MM
    settings_storage['disableConnectionMessage'] = ADDON.getSettingBool("disableConnectionMessage")

    settings_storage['videoMinimumDuration'] = ADDON.getSettingInt("video_MinimumDuration")  # Setting in Minutes. Kodi library uses seconds, needs to be converted.
    settings_storage['video_enableMovie'] = ADDON.getSettingBool("video_Movie")
    settings_storage['video_enableMusicVideo'] = ADDON.getSettingBool("video_MusicVideo")
    settings_storage['video_enableEpisode'] = ADDON.getSettingBool("video_Episode")
    settings_storage['video_enableOther'] = ADDON.getSettingBool("video_Other")

    settings_storage['ambiEnabled'] = ADDON.getSettingBool("group3_enabled")
    validate_schedule()


def convert_time(time):
    hour = int(time.split(":")[0])
    minute = int(time.split(":")[1])
    return datetime.time(hour, minute)
