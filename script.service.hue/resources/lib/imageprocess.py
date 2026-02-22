"""Video frame analysis for ambilight color extraction.

Processes captured video frames to compute average RGB color and brightness
values suitable for driving Hue lights. Based on ScreenBloom by Tyler Kershner.

Uses pixel classification thresholds to exclude very dark and very bright
pixels from the average, producing more perceptually accurate ambient colors.
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

# Based on ScreenBloom by Tyler Kershner
# https://github.com/kershner/screenBloom
# http://www.screenbloom.com/

from PIL import ImageEnhance

from . import timer


class ImageProcess(object):
    """Extracts average color and brightness from video frames for ambilight.

    Uses three pixel intensity thresholds to classify pixels:
        - Below ``LOW_THRESHOLD``: considered too dark, counted but excluded from color average.
        - Between ``LOW_THRESHOLD`` and ``MID_THRESHOLD``: counted as mid-range dark pixels.
        - Above ``HIGH_THRESHOLD``: considered too bright (washed out), excluded entirely.
    """

    def __init__(self):
        self.LOW_THRESHOLD = 10
        self.MID_THRESHOLD = 30
        self.HIGH_THRESHOLD = 240

    @timer
    def img_avg(self, img, min_bri, max_bri, saturation):
        """Compute the average RGB color and brightness from an image.

        Optionally boosts color saturation before processing. Pixels below
        the low threshold or above the high threshold are excluded from the
        color average. The dark pixel ratio drives the brightness calculation.

        Args:
            img: PIL Image in RGBA mode (from Kodi frame capture).
            min_bri: Minimum Hue brightness value (0-100).
            max_bri: Maximum Hue brightness value (0-100).
            saturation: Saturation multiplier (1.0 = no change, >1.0 = boosted).

        Returns:
            Dict with ``"rgb"`` (tuple of floats) and ``"bri"`` (int, Hue brightness).
        """
        dark_pixels = 1
        mid_range_pixels = 1
        total_pixels = 1
        r = 1
        g = 1
        b = 1

        if saturation > 1.0:
            sat_converter = ImageEnhance.Color(img)
            img = sat_converter.enhance(saturation)

        pixels = list(img.getdata())

        for red, green, blue, alpha in pixels:
            if red < self.LOW_THRESHOLD and green < self.LOW_THRESHOLD and blue < self.LOW_THRESHOLD:
                dark_pixels += 1
            elif red > self.HIGH_THRESHOLD and green > self.HIGH_THRESHOLD and blue > self.HIGH_THRESHOLD:
                pass
            else:
                if red < self.MID_THRESHOLD and green < self.MID_THRESHOLD and blue < self.MID_THRESHOLD:
                    mid_range_pixels += 1
                    dark_pixels += 1
                r += red
                g += green
                b += blue
            total_pixels += 1

        pixel_count = len(pixels)
        r_avg = r / pixel_count
        g_avg = g / pixel_count
        b_avg = b / pixel_count
        rgb = [r_avg, g_avg, b_avg]

        # Clamp computed averages to the low threshold minimum
        for index, value in enumerate(rgb):
            if value <= self.LOW_THRESHOLD:
                rgb[index] = self.LOW_THRESHOLD

        rgb = (rgb[0], rgb[1], rgb[2])

        dark_pixel_ratio = float(dark_pixels) / float(total_pixels) * 100
        data = {'rgb': rgb, 'bri': self.get_brightness(min_bri, max_bri, dark_pixel_ratio)}
        return data

    @staticmethod
    def get_brightness(min_bri, max_bri, dark_pixel_ratio):
        """Calculate Hue brightness from the ratio of dark pixels in the frame.

        Higher dark pixel ratios produce lower brightness values. The result
        is scaled to fit within the configured min/max brightness range.

        Args:
            min_bri: Minimum brightness value.
            max_bri: Maximum brightness value.
            dark_pixel_ratio: Percentage of dark pixels in the frame (0-100).

        Returns:
            Brightness value clamped between ``min_bri`` and ``max_bri``.
        """
        normal_range = max(1, max_bri - 1)
        new_range = max_bri - min_bri

        brightness = max_bri - (dark_pixel_ratio * max_bri) / 100
        scaled_brightness = (((brightness - 1) * new_range) / normal_range) + float(min_bri) + 1

        if int(scaled_brightness) < int(min_bri):
            scaled_brightness = int(min_bri)
        elif int(scaled_brightness) > int(max_bri):
            scaled_brightness = int(max_bri)

        return int(scaled_brightness)
