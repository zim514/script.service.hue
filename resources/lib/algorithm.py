import math


def transition_colorspace(hue, light, hsvratio):
    fullspectrum = light.fullspectrum
    h, s, v = hsvratio.hue(
        fullspectrum, hue.settings.ambilight_min, hue.settings.ambilight_max
    )
    hvec = abs(h - light.hue) % int(65535/2)
    hvec = float(hvec/128.0)
    svec = s - light.sat
    vvec = v - light.bri
    # changed to squares for performance
    distance = math.sqrt(hvec**2 + svec**2 + vvec**2)
    if distance > 0:
        duration = int(10 - 2.5 * distance/255)
        light.set_state(hue=h, sat=s, bri=v, transition_time=duration)
