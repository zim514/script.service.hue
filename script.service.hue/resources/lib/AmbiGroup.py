'''
Created on Jul. 2, 2019

@author: Zim514
'''

import time
from threading import Thread
 #https://realpython.com/intro-to-python-threading/#daemon-threads 
#from threading import Timer


from PIL import Image
import colorgram #https://github.com/obskyr/colorgram.py
from .rgbxy import Converter# https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import ColorHelper
from .rgbxy import XYPoint
from .rgbxy import GamutA,GamutB,GamutC

import xbmc

from resources.lib.KodiGroup import KodiGroup
from resources.lib.KodiGroup import VIDEO,ALLMEDIA,AUDIO,STATE_IDLE,STATE_PAUSED,STATE_PLAYING


from . import kodiutils
#from .kodiutils import get_setting,get_setting_as_bool,get_setting_as_int,get_setting_as_float,convertTime
from .qhue import QhueException

import globals
from globals import logger
from .language import get_string as _



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
        
        #self.lights=kodiutils.get_setting("group{}_Interval".format(self.kgroupID))
        self.ambiLights=list(map(int,kodiutils.get_setting("group{}_Lights".format(self.kgroupID)).split(",")))
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        
        super(AmbiGroup,self).setup(bridge, kgroupID, flash=flash, mediaType=1)
        
        self.monitor=monitor

        calls=1/(self.updateInterval)*len(self.ambiLights)  #updateInterval is in seconds, eg. 0.2 for 200ms.  
        logger.debug("callsPerSec: lights: {},interval: {}, calls: {}".format(len(self.ambiLights),self.updateInterval,calls))
        kodiutils.notification(_("Hue Service"), _("Est. Hue Calls/sec (max 10): {}").format(calls),time=10000)

    
    def _getColor(self):
        pass

    def _ambiLoop(self):
        converter=Converter(GamutC)
        helper=ColorHelper(GamutC)
        cap = xbmc.RenderCapture()
        
        
        distance=0.0
        xy=0.51,0.41
        prevxy=0.51,0.41
        logger.debug("AmbiGroup started!")
        while not self.monitor.abortRequested() and self.state == STATE_PLAYING:
            startTime = time.time()
            cap.capture(250, 250) #async capture request to underlying OS
            capImage = cap.getImage() #timeout to wait for OS in ms, default 1000 
            
            image = Image.frombuffer("RGBA", (250, 250), buffer(capImage), "raw", "BGRA")
            
            
            colors = colorgram.extract(image,self.numColors)
            #TODO: RGB min and max configurable.
            if colors[0].rgb.r < 10 and colors[0].rgb.g < 10 and colors[0].rgb.b <10:
                xy=0.5266,0.4133 #max warmth for Gamut C, converted from CT to XY
                #xy=converter.rgb_to_xy(1,1,1)
            else:
                xy=converter.rgb_to_xy(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b)
                xy=(round(xy[0],4),round(xy[1],4)) #Hue has a max precision of 4 decimal points.
            #self._updateHue(xy,2)
            distance=helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1])) #only update hue if XY actually changed
            if distance > 0: 
                for L in self.ambiLights: 
                    x = Thread(target=self._updateHue,name="updateHue", args=(xy,L,self.transitionTime))
                    x.daemon = True
                    x.start()
            
            endTime= time.time()
            
            
            if distance > 0:
                #logger.debug("time: {},Colors: {}, xy: {},prevxy:{}, distance: {}".format(endTime-startTime,colors,xy,prevxy,distance))
                #logger.debug("***** xy: {},prevxy:{}, distance: {}".format(xy,prevxy,distance))
                pass
            else:
                #logger.debug("xy: {},prevxy:{}, distance: {}".format(xy,prevxy,distance))
                pass

            prevxy=xy
            self.monitor.waitForAbort(self.updateInterval) #seconds

        logger.debug("AmbiGroup stopped!")
        
        
        
    
    def _updateHue(self,xy,light,transitionTime):
        #startTime = time.time()
        try:
            self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
        except QhueException as e:
            logger.error("Ambi: Hue call fail: {}".format(e))
        
        #endTime=time.time()
        #logger.debug("_updateHue time: {}".format(endTime-startTime))


