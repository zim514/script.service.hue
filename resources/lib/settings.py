import sys
import logging

import xbmcaddon

from resources.lib import kodilogging
from resources.lib import kodiutils


#ADDON = sys.modules["__main__"].ADDON
ADDON = xbmcaddon.Addon()

#kodilogging.config()
logger = logging.getLogger(ADDON.getAddonInfo('id'))


class Settings():
    def __init__(self, *args, **kwargs):
        self.readxml()

    def readxml(self):

        self.bridge_ip = ADDON.getSetting("bridge_ip")
        self.bridge_user = ADDON.getSetting("bridge_user")

        self.connected = ADDON.getSetting("connected") == "true"
        self.ambilight_group = ADDON.getSetting("ambilight_group")
        self.theater_group = ADDON.getSetting("theater_group")
        self.theater_subgroup = ADDON.getSetting("theater_subgroup")
        self.static_group = ADDON.getSetting("static_group")

        self.dim_time = int(float(ADDON.getSetting("dim_time"))*10)
        self.proportional_dim_time = ADDON.getSetting("proportional_dim_time") == "true"

        self.theater_start_bri_override = ADDON.getSetting("theater_start_bri_override") == "true"
        self.theater_start_bri = int(ADDON.getSetting("theater_start_bri").split(".")[0])

        self.theater_pause_dim_subgroup = ADDON.getSetting("theater_pause_dim_subgroup") == "true"
        self.theater_pause_bri_override = ADDON.getSetting("theater_pause_bri_override") == "true"
        self.theater_pause_bri = int(ADDON.getSetting("theater_pause_bri").split(".")[0])

        self.theater_stop_bri_override = ADDON.getSetting("theater_stop_bri_override") == "true"
        self.theater_stop_bri = int(ADDON.getSetting("theater_stop_bri").split(".")[0])

        self.ambilight_min = int(ADDON.getSetting("ambilight_min").split(".")[0])
        self.ambilight_max = int(ADDON.getSetting("ambilight_max").split(".")[0])

        self.ambilight_threshold_value = int(ADDON.getSetting("ambilight_threshold_value").split(".")[0])
        self.ambilight_threshold_saturation = int(ADDON.getSetting("ambilight_threshold_saturation").split(".")[0])

        self.color_bias = int(ADDON.getSetting("color_bias").split(".")[0])

        self.ambilight_start_dim_enable = ADDON.getSetting("ambilight_start_dim_enable") == "true"
        self.ambilight_start_dim_override = ADDON.getSetting("ambilight_start_dim_override") == "true"
        self.ambilight_start_dim = int(ADDON.getSetting("ambilight_start_dim").split(".")[0])

        self.ambilight_pause_bri_override = ADDON.getSetting("ambilight_pause_bri_override") == "true"
        self.ambilight_pause_bri = int(ADDON.getSetting("ambilight_pause_bri").split(".")[0])

        self.ambilight_stop_bri_override = ADDON.getSetting("ambilight_stop_bri_override") == "true"
        self.ambilight_stop_bri = int(ADDON.getSetting("ambilight_stop_bri").split(".")[0])

        self.static_start_random = ADDON.getSetting("static_start_random") == "true"
        self.static_start_hue_override = ADDON.getSetting("static_start_hue_override") == "true"
        self.static_start_hue = int(ADDON.getSetting("static_start_hue").split(".")[0])
        self.static_start_sat_override = ADDON.getSetting("static_start_sat_override") == "true"
        self.static_start_sat = int(ADDON.getSetting("static_start_sat").split(".")[0])
        self.static_start_bri_override = ADDON.getSetting("static_start_bri_override") == "true"
        self.static_start_bri = int(ADDON.getSetting("static_start_bri").split(".")[0])

        self.misc_initialflash = ADDON.getSetting("misc_initialflash") == "true"
        self.misc_disableshort = ADDON.getSetting("misc_disableshort") == "true"
        self.misc_disableshort_threshold = int(ADDON.getSetting("misc_disableshort_threshold"))
        self.force_light_on = ADDON.getSetting("force_light_on") == "true"

        if self.ambilight_min > self.ambilight_max:
            self.update(ambilight_min=self.ambilight_max)

    def update(self, **kwargs):
        self.__dict__.update(**kwargs)
        for k, v in kwargs.iteritems():
            ADDON.setSetting(k, str(v))

    def __repr__(self):
        return '<Settings\n{}\n>'.format('\n'.join(['{}={}'.format(key, value) for key, value in self.__dict__.items()]))
