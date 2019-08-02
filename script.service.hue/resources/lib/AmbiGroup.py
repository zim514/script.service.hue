# -*- coding: utf-8 -*-
from threading import Thread, Event

from PIL import Image
from . import colorgram #https://github.com/obskyr/colorgram.py
from .rgbxy import Converter,ColorHelper# https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import XYPoint, GamutA,GamutB,GamutC
from .qhue import QhueException

import xbmc,xbmcgui

from . import globals
from . import KodiGroup
from .KodiGroup import VIDEO,AUDIO,ALLMEDIA,STATE_IDLE,STATE_PAUSED,STATE_PLAYING
from . import kodiHue

from .globals import logger
from .recipes import HUE_RECIPES
from .language import get_string as _


class AmbiGroup(KodiGroup.KodiGroup):
    def onAVStarted(self):
        logger.info("Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(self.kgroupID, self.enabled,self.isPlayingVideo(),self.isPlayingAudio(),self.mediaType,self.playbackType()))
        logger.info("Ambilight Settings. Colours: {}, Interval: {}, transitionTime: {}".format(self.numColors,self.updateInterval,self.transitionTime))
        logger.info("Ambilight Settings. enabled: {}, forceOn: {}, setBrightness: {}, Brightness: {}".format(self.enabled,self.forceOn,self.setBrightness,self.brightness))
        self.checkVideoActivation()
        self.state = STATE_PLAYING
        if self.enabled and self.checkActiveTime() and self.checkVideoActivation():
            self.ambiRunning.set()
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
        self.ambiRunning.clear()
        self.state = STATE_IDLE


    def onPlayBackPaused(self):
        logger.info("In ambiGroup[{}], onPlaybackPaused()".format(self.kgroupID))
        self.ambiRunning.clear()
        self.state = STATE_PAUSED
        

    
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
        self.minimumDistance=globals.ADDON.getSettingInt("group{}_ColorDifference".format(self.kgroupID)) / 10000 #convert to float with 4 precision between 0-1

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
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        self.ambiRunning = Event()
        super(AmbiGroup,self).setup(bridge, kgroupID, flash=flash, mediaType=1)
        self.monitor=monitor
        
        #=======================================================================
        # calls=1/(self.updateInterval)*len(self.ambiLights)  #updateInterval is in seconds, eg. 0.2 for 200ms.
        # if calls > 25 and calls < 2000:
        #     kodiHue.notification(_("Hue Service"), _("Est. Hue Commands/sec (max 20): {}").format(calls),time=3000,icon=xbmcgui.NOTIFICATION_WARNING)
        # else:
        #     logger.warn("Warning: 0 update interval ")
        #     kodiHue.notification(_("Hue Service"), _("Recommended minimum update interval: 100ms").format(calls),time=3000,icon=xbmcgui.NOTIFICATION_WARNING)
        # logger.debug("callsPerSec: lights: {},interval: {}, calls: {}".format(len(self.ambiLights),self.updateInterval,calls))
        #=======================================================================
    
    
    def _ambiLoop(self):
        
        cap = xbmc.RenderCapture()
        logger.debug("_ambiLoop started")
        try:
            while not self.monitor.abortRequested() and self.ambiRunning.is_set():
                try:
                    cap.capture(self.captureSize, self.captureSize) #async capture request to underlying OS
                    capImage = cap.getImage() #timeout to wait for OS in ms, default 1000
                    if capImage is None or len(capImage) < 50:
                        logger.error("capImage is none or <50: {},{}".format(len(capImage),capImage))
                        break #no image captured, try again next iteration
                    image = Image.frombuffer("RGBA", (self.captureSize, self.captureSize), buffer(capImage), "raw", "BGRA")
                except ValueError:
                    logger.error("capImage: {},{}".format(len(capImage),capImage))
                    logger.error("Value Error")
                    break #returned capture is  smaller than expected when player stopping. give up this loop.
                except Exception as ex:
                    logger.warning("Capture exception",exc_info=1)
                    break 
                
                colors = colorgram.extract(image,self.numColors)
        
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
        if distance > self.minimumDistance:
            try:
                self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
            except QhueException as ex:
                logger.exception("Ambi: Hue call fail:")
        else:
            #logger.debug("Distance too small: min: {}, current: {}".format(self.minimumDistance,distance))
            pass
        self.ambiLights[light].update(prevxy=xy)



    def _updateHueXY(self,xy,light,transitionTime):
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
        if distance > self.minimumDistance:
            try:
                self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
            except QhueException as ex:
                logger.exception("Ambi: Hue call fail:")
        else: 
            #logger.debug("Distance too small: min: {}, current: {}".format(self.minimumDistance,distance))
            pass
        self.ambiLights[light].update(prevxy=xy)
