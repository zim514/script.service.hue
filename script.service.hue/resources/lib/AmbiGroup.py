'''
Created on Jul. 2, 2019

@author: Zim514
'''

import time
from threading import Thread



from PIL import Image
from . import colorgram #https://github.com/obskyr/colorgram.py
from .rgbxy import Converter# https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import ColorHelper
from .rgbxy import XYPoint
from .rgbxy import GamutA,GamutB,GamutC

from xbmc import RenderCapture
from xbmcgui import NOTIFICATION_WARNING

from resources.lib.KodiGroup import KodiGroup
from resources.lib.KodiGroup import VIDEO,AUDIO,ALLMEDIA,STATE_IDLE,STATE_PAUSED,STATE_PLAYING
from .kodiHue import getLightGamut


from . import kodiutils
from .qhue import QhueException

from . import globals
from .globals import logger
from .recipes import HUE_RECIPES
from .language import get_string as _
from resources.lib.globals import timer


class AmbiGroup(KodiGroup):
    def onAVStarted(self):
        logger.info("Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(self.kgroupID, self.enabled,self.isPlayingVideo(),self.isPlayingAudio(),self.mediaType,self.playbackType()))
        logger.info("Ambilight Settings. Colours: {}, Interval: {}, transitionTime: {}".format(self.numColors,self.updateInterval,self.transitionTime))
        logger.info("Ambilight Settings. enabled: {}, forceOn: {}, setBrightness: {}, Brightness: {}".format(self.enabled,self.forceOn,self.setBrightness,self.brightness))
        
        if self.enabled and self.activeTime() and self.playbackType() == 1:
            self.state = STATE_PLAYING
            if self.forceOn:
                for L in self.ambiLights:
                    try:
                        self.bridge.lights[L].state(on=True)
                    except QhueException as e:
                        logger.debug("Ambi: Initial Hue call fail: {}".format(e))

            if self.setBrightness:
                for L in self.ambiLights:
                    try:
                        self.bridge.lights[L].state(bri=self.brightness)
                    except QhueException as e:
                        logger.debug("Ambi: Initial Hue call fail: {}".format(e))
            
            ambiLoopThread=Thread(target=self._ambiLoop,name="_ambiLoop")
            ambiLoopThread.daemon = True
            ambiLoopThread.start()


    def onPlayBackStopped(self):
        logger.info("In ambiGroup[{}], onPlaybackStopped()".format(self.kgroupID))
        self.state = STATE_IDLE


    def onPlayBackPaused(self):
        logger.info("In ambiGroup[{}], onPlaybackPaused()".format(self.kgroupID))
        self.state = STATE_PAUSED

    
    def readSettings(self):
        self.enabled=kodiutils.get_setting_as_bool("group{}_enabled".format(self.kgroupID))
        
        self.updateInterval=kodiutils.get_setting_as_float("group{}_Interval".format(self.kgroupID)) /1000#
        self.numColors=kodiutils.get_setting_as_int("group{}_NumColors".format(self.kgroupID))
        self.transitionTime =  kodiutils.get_setting_as_int("group{}_TransitionTime".format(self.kgroupID)) /100 #This is given as a multiple of 100ms and defaults to 4 (400ms). For example, setting transitiontime:10 will make the transition last 1 second.
        
        self.forceOn=kodiutils.get_setting_as_bool("group{}_forceOn".format(self.kgroupID))
        self.setBrightness=kodiutils.get_setting_as_bool("group{}_setBrightness".format(self.kgroupID))
        self.brightness=kodiutils.get_setting_as_int("group{}_Brightness".format(self.kgroupID))*255/100#convert percentage to value 1-254
        self.blackFilter=kodiutils.get_setting_as_int("group{}_BlackFilter".format(self.kgroupID))
        self.whiteFilter=kodiutils.get_setting_as_int("group{}_WhiteFilter".format(self.kgroupID))
        self.defaultRecipe=kodiutils.get_setting_as_int("group{}_DefaultRecipe".format(self.kgroupID))
        self.captureSize=kodiutils.get_setting_as_int("group{}_CaptureSize".format(self.kgroupID))
        
        
        self.ambiLights={}
        lightIDs=kodiutils.get_setting("group{}_Lights".format(self.kgroupID)).split(",")
        
        index=0
        for L in lightIDs:
            gamut=getLightGamut(self.bridge,L)
            light={L:{'gamut': gamut,'prevxy': (0,0),"index":index}}
            self.ambiLights.update(light)
            index=index+1
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        
        super(AmbiGroup,self).setup(bridge, kgroupID, flash=flash, mediaType=1)
        
        self.monitor=monitor
        
        try:
            calls=0
            calls=1/(self.updateInterval)*len(self.ambiLights)  #updateInterval is in seconds, eg. 0.2 for 200ms.
            if calls > 25:
                kodiutils.notification(_("Hue Service"), _("Est. Hue Commands/sec (max 20): {}").format(calls),time=000,icon=NOTIFICATION_WARNING)
        except ZeroDivisionError:
            logger.error("Exception: 0 update interval warning")
            kodiutils.notification(_("Hue Service"), _("Recommended minimum update interval: 100ms").format(calls),time=5000,icon=NOTIFICATION_WARNING)
        logger.debug("callsPerSec: lights: {},interval: {}, calls: {}".format(len(self.ambiLights),self.updateInterval,calls))

    
    def _getColor(self):
        pass
    
    
    def _ambiLoop(self):
        
        cap = RenderCapture()
        
        logger.debug("AmbiGroup started")
        try:
            while not self.monitor.abortRequested() and self.state == STATE_PLAYING:
                self._ambiUpdate(cap)
                self.monitor.waitForAbort(self.updateInterval) #seconds
        except Exception as ex:
            logger.exception("Exception in _ambiLoop")
            

        logger.debug("AmbiGroup stopped")
        
    @timer
    def _ambiUpdate(self,cap):
            try:
                cap.capture(self.captureSize, self.captureSize) #async capture request to underlying OS
                capImage = cap.getImage(100) #timeout to wait for OS in ms, default 1000
                image = Image.frombuffer("RGBA", (self.captureSize, self.captureSize), buffer(capImage), "raw", "BGRA")
            except Exception as ex:
                logger.exception("Capture exception")
                return 
            
            colors = colorgram.extract(image,self.numColors)

            if (colors[0].rgb.r < self.blackFilter and colors[0].rgb.g < self.blackFilter and colors[0].rgb.b <self.blackFilter) or \
            (colors[0].rgb.r > self.whiteFilter and colors[0].rgb.g > self.whiteFilter and colors[0].rgb.b > self.whiteFilter):
                #logger.debug("rgb filter: r,g,b: {},{},{}".format(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b))
                xy=HUE_RECIPES[self.defaultRecipe]["xy"]
                
                for L in self.ambiLights: 
                    x = Thread(target=self._updateHueXY,name="updateHue", args=(xy,L,self.transitionTime))
                    x.daemon = True
                    x.start()
                
            else:
                for L in self.ambiLights:
                    if self.numColors == 1:
                        #logger.debug("AmbiUpdate 1 Color: r,g,b: {},{},{}".format(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b))
                        x = Thread(target=self._updateHueRGB,name="updateHue", args=(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b,L,self.transitionTime))
                    else:
                        
                        colorIndex=self.ambiLights[L]["index"] % len(colors)
                        #logger.debug("AmbiUpdate Colors: {}".format(colors))
                        x = Thread(target=self._updateHueRGB,name="updateHue", args=(colors[colorIndex].rgb.r,colors[colorIndex].rgb.g,colors[colorIndex].rgb.b,L,self.transitionTime))
                    x.daemon = True
                    x.start()
    @timer
    def _updateHueRGB(self,r,g,b,light,transitionTime):
        #startTime = time.time()
        
        gamut=self.ambiLights[light].get('gamut')
        prevxy=self.ambiLights[light].get('prevxy')
        
        if gamut == "A":
            converter=Converter(GamutA)
            helper=ColorHelper(GamutA)
        elif gamut == "B":
            converter=Converter(GamutB)
            helper=ColorHelper(GamutB)
        elif gamut == "C":
            converter=Converter(GamutC)
            helper=ColorHelper(GamutC)
        
        xy=converter.rgb_to_xy(r,g,b)
        xy=round(xy[0],4),round(xy[1],4) #Hue has a max precision of 4 decimal points.

        distance=round(helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1])) ,4)#only update hue if XY actually changed
        if distance > 0:
            try:
                self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
            except QhueException as ex:
                logger.exception("Ambi: Hue call fail:")
        
        
        #endTime=time.time()
        #logger.debug("time: {},distance: {}".format(int((endTime-startTime)*1000),distance))
        self.ambiLights[light].update(prevxy=xy)
        
    @timer
    def _updateHueXY(self,xy,light,transitionTime):
        #startTime = time.time()
        
        gamut=self.ambiLights[light].get('gamut')
        prevxy=self.ambiLights[light].get('prevxy')
        
        if gamut == "A":
            helper=ColorHelper(GamutA)
        elif gamut == "B":
            helper=ColorHelper(GamutB)
        elif gamut == "C":
            helper=ColorHelper(GamutC)
        

        xy=(round(xy[0],4),round(xy[1],4)) #Hue has a max precision of 4 decimal points.

        distance=round(helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1])) ,4)#only update hue if XY actually changed
        if distance > 0:
            try:
                self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
            except QhueException as ex:
                logger.exception("Ambi: Hue call fail:")
        

        #endTime=time.time()
        #logger.debug("time: {},distance: {}".format(int((endTime-startTime)*1000),distance))
        self.ambiLights[light].update(prevxy=xy)
