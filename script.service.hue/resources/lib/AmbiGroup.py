# -*- coding: utf-8 -*-
from threading import Thread, Event

import xbmc,xbmcgui
from PIL import Image

from . import colorgram #https://github.com/obskyr/colorgram.py
from .rgbxy import Converter,ColorHelper# https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA,GamutB,GamutC
from .qhue import QhueException

from . import globals
from . import KodiGroup
from .KodiGroup import VIDEO,AUDIO,ALLMEDIA,STATE_STOPPED,STATE_PAUSED,STATE_PLAYING
from . import kodiHue

from .globals import logger
from .recipes import HUE_RECIPES
from .language import get_string as _


class AmbiGroup(KodiGroup.KodiGroup):
    def onAVStarted(self):
        logger.info("Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(self.enabled,self.isPlayingVideo(),self.isPlayingAudio(),self.mediaType,self.playbackType()))
        logger.info("Ambilight Settings: Colours: {}, Interval: {}, transitionTime: {}".format(self.numColors,self.updateInterval,self.transitionTime))
        logger.info("Ambilight Settings: forceOn: {}, setBrightness: {}, Brightness: {}, MinimumDistance: {}".format(self.forceOn,self.setBrightness,self.brightness,self.minimumDistance))
        self.state = STATE_PLAYING
        
        if self.isPlayingVideo():
            self.videoInfoTag=self.getVideoInfoTag()
            if self.enabled and self.checkActiveTime() and self.checkVideoActivation(self.videoInfoTag):

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
                
                self.ambiRunning.set()
                ambiLoopThread=Thread(target=self._ambiLoop,name="_ambiLoop")
                ambiLoopThread.daemon = True
                ambiLoopThread.start()


    def onPlayBackStopped(self):
        logger.info("In ambiGroup[{}], onPlaybackStopped()".format(self.kgroupID))
        self.state = STATE_STOPPED
        self.ambiRunning.clear()


    def onPlayBackPaused(self):
        logger.info("In ambiGroup[{}], onPlaybackPaused()".format(self.kgroupID))
        self.state = STATE_PAUSED
        self.ambiRunning.clear()

    
    def loadSettings(self):
        logger.debug("AmbiGroup Load settings")
        
        self.enabled=globals.ADDON.getSettingBool("group{}_enabled".format(self.kgroupID))
        
        self.numColors=globals.ADDON.getSettingInt("group{}_NumColors".format(self.kgroupID))
        self.transitionTime =  globals.ADDON.getSettingInt("group{}_TransitionTime".format(self.kgroupID)) /100 #This is given as a multiple of 100ms and defaults to 4 (400ms). For example, setting transitiontime:10 will make the transition last 1 second.
        self.forceOn=globals.ADDON.getSettingBool("group{}_forceOn".format(self.kgroupID))
        self.setBrightness=globals.ADDON.getSettingBool("group{}_setBrightness".format(self.kgroupID))
        self.brightness=globals.ADDON.getSettingInt("group{}_Brightness".format(self.kgroupID))*255/100#convert percentage to value 1-254
        self.blackFilter=globals.ADDON.getSettingInt("group{}_BlackFilter".format(self.kgroupID))
        self.defaultRecipe=globals.ADDON.getSettingInt("group{}_DefaultRecipe".format(self.kgroupID))
        self.captureSize=globals.ADDON.getSettingInt("group{}_CaptureSize".format(self.kgroupID))
        self.minimumDistance=float(globals.ADDON.getSettingInt("group{}_ColorDifference".format(self.kgroupID))) / 10000 #convert to float with 4 precision between 0-1
        self.minimumColorProportion=float(globals.ADDON.getSettingInt("group{}_MinimumColorProportion".format(self.kgroupID))) /100 #convert percentage to float 0-1

        self.updateInterval=globals.ADDON.getSettingInt("group{}_Interval".format(self.kgroupID)) /1000# convert MS to seconds
        if self.updateInterval == 0: 
            self.updateInterval = 0.002
        
        self.ambiLights={}
        lightIDs=globals.ADDON.getSetting("group{}_Lights".format(self.kgroupID)).split(",")
        index=0
        for L in lightIDs:
            gamut=kodiHue.getLightGamut(self.bridge,L)
            light={L:{'gamut': gamut,'prevxy': (0,0),"index":index}}
            self.ambiLights.update(light)
            index=index+1
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False):
        self.ambiRunning = Event()
        super(AmbiGroup,self).setup(bridge, kgroupID, flash, VIDEO)
        self.monitor=monitor
        
        
        self.converterA=Converter(GamutA)
        self.converterB=Converter(GamutB)
        self.converterC=Converter(GamutC)
        self.helper=ColorHelper(GamutC)


    
    def _ambiLoop(self):
        
        cap = xbmc.RenderCapture()
        logger.debug("_ambiLoop started")
        expectedCaptureSize= self.captureSize*self.captureSize*4 #size * 4 bytes I guess
        
        for L in self.ambiLights: 
            self.ambiLights[L].update(prevxy=(0.0001,0.0001))
        
        try:
            while not self.monitor.abortRequested() and self.ambiRunning.is_set(): #loop until kodi tells add-on to stop or video playing flag is unset.
                try:
                    cap.capture(self.captureSize, self.captureSize) #async capture request to underlying OS
                    capImage = cap.getImage() #timeout to wait for OS in ms, default 1000
                    #logger.debug("CapSize: {}".format(len(capImage)))
                    if capImage is None or len(capImage) < expectedCaptureSize:
                        logger.error("capImage is none or < expected: {}, expected: {}".format(len(capImage),expectedCaptureSize))
                        self.monitor.waitForAbort(0.25) #pause before trying again
                        continue #no image captured, try again next iteration
                    image = Image.frombuffer("RGBA", (self.captureSize, self.captureSize), buffer(capImage), "raw", "BGRA")
                except ValueError:
                    logger.error("capImage: {}".format(len(capImage)))
                    logger.error("Value Error")
                    self.monitor.waitForAbort(0.25)
                    continue #returned capture is  smaller than expected when player stopping. give up this loop.
                except Exception as ex:
                    logger.warning("Capture exception",exc_info=1)
                    self.monitor.waitForAbort(0.25)
                    continue 
                
                colors = colorgram.extract(image,self.numColors)
                #logger.debug("proportion: {0:.0%}".format(colors[0].proportion))
                if colors[0].proportion > self.minimumColorProportion:
                    if colors[0].rgb.r < self.blackFilter and colors[0].rgb.g < self.blackFilter and colors[0].rgb.b <self.blackFilter:
                        #logger.debug("rgb filter: r,g,b: {},{},{}".format(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b))
                        if self.defaultRecipe: #defaultRecipe=0: Do nothing
                            xy=HUE_RECIPES[self.defaultRecipe]["xy"]#Apply XY value from default recipe setting
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
                            
                            
                            self.monitor.waitForAbort(self.updateInterval) #seconds
        except Exception as ex:
            logger.exception("Exception in _ambiLoop")
        logger.debug("_ambiLoop stopped")


    def _updateHueRGB(self,r,g,b,light,transitionTime):
        gamut=self.ambiLights[light].get('gamut')
        prevxy=self.ambiLights[light].get('prevxy')
        
        if gamut == "A":
            converter=self.converterA
        elif gamut == "B":
            converter=self.converterB
        elif gamut == "C":
            converter=self.converterC

        
        xy=converter.rgb_to_xy(r,g,b)
        xy=round(xy[0],3),round(xy[1],3) #Hue has a max precision of 4 decimal points, but three is plenty, lower is not noticable.

        #distance=self.helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1]))#only update hue if XY changed enough
        #if distance > self.minimumDistance:
        try:
            self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
        except QhueException as ex:
            logger.exception("Ambi: Hue call fail")
        self.ambiLights[light].update(prevxy=xy)


    def _updateHueXY(self,xy,light,transitionTime):
        prevxy=self.ambiLights[light].get('prevxy')
        
        #xy=(round(xy[0],3),round(xy[1],3)) #Hue has a max precision of 4 decimal points.

        #distance=self.helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1]))#only update hue if XY changed enough
        #if distance > self.minimumDistance:
        try:
            self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
        except QhueException as ex:
            logger.exception("Ambi: Hue call fail")
    
        self.ambiLights[light].update(prevxy=xy)
