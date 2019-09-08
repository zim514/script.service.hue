# -*- coding: utf-8 -*-
#original version by https://github.com/obskyr/colorgram.py
#modified by Snapcase for performance
from __future__ import unicode_literals
from __future__ import division

from ..globals import timer
from ..globals import logger

import array
from collections import namedtuple
from PIL import Image

import sys
if sys.version_info[0] <= 2:
    range = xrange
    ARRAY_DATATYPE = b'l'
else:
    ARRAY_DATATYPE = 'l'

Rgb = namedtuple('Rgb', ('r', 'g', 'b'))

class Color(object):
    def __init__(self, r, g, b, proportion):
        self.rgb = Rgb(r, g, b)
        self.proportion = proportion
    
    def __repr__(self):
        return "<colorgram.py Color: {}, {}%>".format(
            str(self.rgb), str(self.proportion * 100))

@timer
def extract(image, number_of_colors):
    #image = inputImage
    #logger.debug("Image Mode {}".format(image.mode))
    #if image.mode not in ('RGB', 'RGBA', 'RGBa'):
    #image = image.convert('RGB')

    totalPixels=image.size[0] * image.size[1]
    
    samples = sample(image)
    used = pick_used(samples)
    used.sort(key=lambda x: x[0], reverse=True)
    return get_colors(samples, used, number_of_colors,totalPixels)


def sample(image):
    top_two_bits = 0b11000000

    sides = 1 << 2 # Left by the number of bits used.
    cubes = sides ** 3

    samples = array.array(ARRAY_DATATYPE, (0 for _ in range(cubes*4)))
    width, height = image.size
    
    pixels = image.load()
    [_process(samples,pixels,x,y,top_two_bits) for x in range(width) for y in range(height)] #python2.7&3 ~60-65ms on dev machine w/ BBBunny
    #map(lambda x: map(lambda y: _process(samples,pixels,x,y,top_two_bits), range(height)), range(width)) #python2.7&3 ~70ms on dev machine w/ BBBunny
    #imap(lambda x: imap(lambda y: (samples = _process(samples,pixels,x,y,top_two_bits))), range(height)), range(width))
    
    
    # #python2.7 ~70ms on dev machine w/ BBBunny:
    #for y in range(height): 
    #    for x in range(width):
    #        samples=_process(samples, pixels, x, y, top_two_bits)
    return samples

def _process(samples,pixels,x,y,top_two_bits):
    # Pack the top two bits of all 6 values into 12 bits.
    # 0bYYhhllrrggbb - luminance, hue, luminosity, red, green, blue.

    r, g, b = pixels[x, y][:3]
    #h, s, l = hsl(r, g, b)
    # Standard constants for converting RGB to relative luminance.
    #Y = int(r * 0.2126 + g * 0.7152 + b * 0.0722)

    # Everything's shifted into place from the top two
    # bits' original position - that is, bits 7-8.
    #packed = (Y & top_two_bits) >> 2
    #packed |= (h & top_two_bits) >> 4
    #packed |= (l & top_two_bits) >> 6

    # Due to a bug in the original colorgram.js, RGB isn't included.
    # The original author tries using negative bit shifts, while in
    # fact JavaScript has the stupidest possible behavior for those.
    # By uncommenting these lines, "intended" behavior can be
    # restored, but in order to keep result compatibility with the
    # original the "error" exists here too. Add back in if it is
    # ever fixed in colorgram.js.

    packed = (r & top_two_bits) >> 2
    packed |= (g & top_two_bits) >> 4
    packed |= (b & top_two_bits) >> 6
    # print "Pixel #{}".format(str(y * width + x))
    # print "h: {}, s: {}, l: {}".format(str(h), str(s), str(l))
    # print "R: {}, G: {}, B: {}".format(str(r), str(g), str(b))
    # print "Y: {}".format(str(Y))
    # print "Packed: {}, binary: {}".format(str(packed), bin(packed)[2:])
    # print
    packed *= 4
    samples[packed] += r
    samples[packed + 1] += g
    samples[packed + 2] += b
    samples[packed + 3] += 1
    return

def pick_used(samples):
    used = []
    for i in range(0, len(samples), 4):
        count = samples[i + 3]
        if count:
            used.append((count, i))
    return used

def get_colors(samples, used, number_of_colors,totalPixels):

    colors = []
    number_of_colors = min(number_of_colors, len(used))

    for count, index in used[:number_of_colors]:


        color = Color(
            samples[index]     // count,
            samples[index + 1] // count,
            samples[index + 2] // count,
            count
        )

        colors.append(color)
    for color in colors:
        color.proportion /= totalPixels
    return colors


# Useful snippet for testing values:
# print "Pixel #{}".format(str(y * width + x))
# print "h: {}, s: {}, l: {}".format(str(h), str(s), str(l))
# print "R: {}, G: {}, B: {}".format(str(r), str(g), str(b))
# print "Y: {}".format(str(Y))
# print "Packed: {}, binary: {}".format(str(packed), bin(packed)[2:])
# print

# And on the JS side:
# var Y = ~~(img.data[i] * 0.2126 + img.data[i + 1] * 0.7152 + img.data[i + 2] * 0.0722);
# console.log("Pixel #" + i / img.channels);
# console.log("h: " + h[0] + ", s: " + h[1] + ", l: " + h[2]);
# console.log("R: " + img.data[i] + ", G: " + img.data[i + 1] + ", B: " + img.data[i + 2]);
# console.log("Y: " + Y);
# console.log("Packed: " + v + ", binary: " + (v >>> 0).toString(2));
# console.log();
