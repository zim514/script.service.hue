# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
from threading import Event

from resources.lib import kodiutils
from resources.lib import kodilogging
from resources.lib import settings

from resources.lib.newDefault import Hue
from resources.lib.newDefault import MyMonitor
from resources.lib.newDefault import MyPlayer

import xbmc
import xbmcaddon



__addon__ = xbmcaddon.Addon()
__addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__cwd__ = __addon__.getAddonInfo('path')


from resources.lib import algorithm
from resources.lib.ambilight_controller import AmbilightController
from resources.lib import bridge
from resources.lib import image
from resources.lib import ui


from resources.lib.settings import Settings
from resources.lib.static_controller import StaticController
from resources.lib.theater_controller import TheaterController
from resources.lib.tools import get_version
from resources.lib import kodilogging

from resources.lib import kodiutils



ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))

REMOTE_DBG = True



logger.debug("Kodi Hue: In .(argv={}) service started, version: {}, SYSPATH: {}".format(
    sys.argv, get_version(),sys.path))


ev = Event()
capture = xbmc.RenderCapture()
fmt = capture.getImageFormat()
# BGRA or RGBA
fmtRGBA = fmt == 'RGBA'





##################################################
## RUN
###################



def run():
    logger.debug("Kodi Hue: In .(argv={}) service started, version: {}, SYSPATH: {}".format(
        sys.argv, get_version(),sys.path))
    
    
    ev = Event()
    capture = xbmc.RenderCapture()
    fmt = capture.getImageFormat()
    # BGRA or RGBA
    fmtRGBA = fmt == 'RGBA'

    settings = Settings()
    monitor = MyMonitor(settings)   

    args = None
    if len(sys.argv) == 2:
        args = sys.argv[1]

    hue = Hue(settings, args)

    
    
        
 
    
######################    
#    monitor = xbmc.Monitor()
#
#    while not monitor.abortRequested():
#        # Sleep/wait for abort for 10 seconds
#        if monitor.waitForAbort(10):
#            # Abort was requested while waiting. We should exit
#            break
#        logger.debug("hello addon! %s" % time.time())
#
####################
    player = MyPlayer()
    
    
    while not hue.connected and not monitor.abortRequested():
            time.sleep(0.1)
   
    
    if player is None:
        logger.debug('Kodi Hue: In run() could not instantiate player')
        return

    while not monitor.abortRequested():
        if len(hue.ambilight_controller.lights) and not ev.is_set():
            startReadOut = False
            vals = {}
            if player.playingvideo:  # only if there's actually video
                try:
                    vals = capture.getImage(200)
                    if len(vals) > 0 and player.playingvideo:
                        startReadOut = True
                    if startReadOut:
                        screen = image.Screenshot(
                            capture.getImage())
                        hsv_ratios = screen.spectrum_hsv(
                            screen.pixels,
                            hue.settings.ambilight_threshold_value,
                            hue.settings.ambilight_threshold_saturation,
                            hue.settings.color_bias,
                            len(hue.ambilight_controller.lights)
                        )
                        for i in range(len(hue.ambilight_controller.lights)):
                            algorithm.transition_colorspace(
                                hue, hue.ambilight_controller.lights.values()[i], hsv_ratios[i], )
                except ZeroDivisionError:
                    pass

        if monitor.waitForAbort(0.1):
            logger.debug('Kodi Hue: In run() deleting player')
            del player  # might help with slow exit.
            break
        
        
        
        