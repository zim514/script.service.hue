import sys
import xbmcaddon

__addon__      = sys.modules[ "__main__" ].__addon__

class settings():
  def __init__( self, *args, **kwargs ):
    self.readxml()
    self.addon = xbmcaddon.Addon()

  def readxml(self):
    self.bridge_ip             = __addon__.getSetting("bridge_ip")
    self.bridge_user           = __addon__.getSetting("bridge_user")

    self.mode                  = int(__addon__.getSetting("mode"))
    self.light                 = int(__addon__.getSetting("light"))
    self.light1_id             = int(__addon__.getSetting("light1_id"))
    self.light2_id             = int(__addon__.getSetting("light2_id"))
    self.light3_id             = int(__addon__.getSetting("light3_id"))
    self.group_id              = int(__addon__.getSetting("group_id"))
    self.misc_initialflash     = __addon__.getSetting("misc_initialflash") == "true"
    self.misc_disableshort     = __addon__.getSetting("misc_disableshort") == "true"
    self.misc_disableshort_threshold = int(__addon__.getSetting("misc_disableshort_threshold") == "true")

    self.dimmed_bri            = int(int(__addon__.getSetting("dimmed_bri").split(".")[0])*254/100)
    self.override_undim_bri    = __addon__.getSetting("override_undim_bri") == "true"
    self.undim_bri             = int(int(__addon__.getSetting("undim_bri").split(".")[0])*254/100)
    self.override_paused       = __addon__.getSetting("override_paused") == "true"
    self.paused_bri            = int(int(__addon__.getSetting("paused_bri").split(".")[0])*254/100)
    self.dim_time              = int(float(__addon__.getSetting("dim_time"))*10)
    self.proportional_dim_time = __addon__.getSetting("proportional_dim_time") == "true"
    self.override_hue          = __addon__.getSetting("override_hue") == "true"
    self.dimmed_hue            = int(__addon__.getSetting("dimmed_hue").split(".")[0])
    self.undim_hue             = int(__addon__.getSetting("undim_hue").split(".")[0])
    self.override_sat          = __addon__.getSetting("override_sat") == "true"
    self.dimmed_sat            = int(__addon__.getSetting("dimmed_sat").split(".")[0])
    self.undim_sat             = int(__addon__.getSetting("undim_sat").split(".")[0])
    self.undim_during_credits  = __addon__.getSetting("undim_during_credits") == "true"
    self.credits_delay_time    = int(__addon__.getSetting("credits_delay_time").split(".")[0])
    self.ambilight_dim         = __addon__.getSetting("ambilight_dim") == "true"
    self.ambilight_dim_light   = int(__addon__.getSetting("ambilight_dim_light"))
    self.ambilight_dim_light1_id = int(__addon__.getSetting("ambilight_dim_light1_id"))
    self.ambilight_dim_light2_id = int(__addon__.getSetting("ambilight_dim_light2_id"))
    self.ambilight_dim_light3_id = int(__addon__.getSetting("ambilight_dim_light3_id"))
    self.ambilight_dim_group_id = int(__addon__.getSetting("ambilight_dim_group_id"))
    self.ambilight_min         = int(int(__addon__.getSetting("ambilight_min").split(".")[0])*254/100)
    self.ambilight_max         = int(int(__addon__.getSetting("ambilight_max").split(".")[0])*254/100)
    self.ambilight_threshold_value = int(int(__addon__.getSetting("ambilight_threshold_value").split(".")[0])*254/100)
    self.ambilight_threshold_saturation = int(int(__addon__.getSetting("ambilight_threshold_saturation").split(".")[0])*254/100)
    self.color_bias            = int(int(__addon__.getSetting("color_bias").split(".")[0])/3*3)
    self.force_light_on        = __addon__.getSetting("force_light_on") == "true"
    self.force_light_group_start_override = __addon__.getSetting("force_light_group_start_override") == "true"

    if self.ambilight_min > self.ambilight_max:
        self.ambilight_min = self.ambilight_max
        __addon__.setSetting("ambilight_min", __addon__.getSetting("ambilight_max"))

    self.debug                 = __addon__.getSetting("debug") == "true"

  def update(self, **kwargs):
    self.__dict__.update(**kwargs)
    for k, v in kwargs.iteritems():
      self.addon.setSetting(k, v)

  def __repr__(self):
    return 'bridge_ip: %s\n' % self.bridge_ip + \
    'bridge_user: %s\n' % self.bridge_user + \
    'mode: %s\n' % str(self.mode) + \
    'light: %s\n' % str(self.light) + \
    'light1_id: %s\n' % str(self.light1_id) + \
    'light2_id: %s\n' % str(self.light2_id) + \
    'light3_id: %s\n' % str(self.light3_id) + \
    'group_id: %s\n' % str(self.group_id) + \
    'misc_initialflash: %s\n' % str(self.misc_initialflash) + \
    'misc_disableshort: %s\n' % str(self.misc_disableshort) + \
    'misc_disableshort_threshold: %s\n' % str(self.misc_disableshort_threshold) + \
    'dimmed_bri: %s\n' % str(self.dimmed_bri) + \
    'undim_bri: %s\n' % str(self.undim_bri) + \
    'override_paused: %s\n' % str(self.override_paused) + \
    'paused_bri: %s\n' % str(self.paused_bri) + \
    'dimmed_hue: %s\n' % str(self.dimmed_hue) + \
    'override_hue: %s\n' % str(self.override_hue) + \
    'undim_hue: %s\n' % str(self.undim_hue) + \
    'dimmed_sat: %s\n' % str(self.dimmed_sat) + \
    'override_sat: %s\n' % str(self.override_sat) + \
    'undim_sat: %s\n' % str(self.undim_sat) + \
    'ambilight_dim: %s\n' % str(self.ambilight_dim) + \
    'ambilight_dim_light: %s\n' % str(self.ambilight_dim_light) + \
    'ambilight_dim_light1_id: %s\n' % str(self.ambilight_dim_light1_id) + \
    'ambilight_dim_light2_id: %s\n' % str(self.ambilight_dim_light2_id) + \
    'ambilight_dim_light3_id: %s\n' % str(self.ambilight_dim_light3_id) + \
    'ambilight_dim_group_id: %s\n' % str(self.ambilight_dim_group_id) + \
    'ambilight_min: %s\n' % str(self.ambilight_min) + \
    'ambilight_max: %s\n' % str(self.ambilight_max) + \
    'ambilight_threshold_value: %s\n' % str(self.ambilight_threshold_value) + \
    'ambilight_threshold_saturation: %s\n' % str(self.ambilight_threshold_saturation) + \
    'color_bias: %s\n' % str(self.color_bias) + \
    'force_light_on: %s\n' % str(self.force_light_on) + \
    'force_light_group_start_override: %s\n' % str(self.force_light_group_start_override) + \
    'debug: %s\n' % self.debug
