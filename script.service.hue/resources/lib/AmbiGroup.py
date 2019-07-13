'''
Created on Jul. 2, 2019

@author: Zim514
'''
import io
import time
import threading #https://realpython.com/intro-to-python-threading/#daemon-threads 
#from threading import Timer


from PIL import Image
import colorgram #https://github.com/obskyr/colorgram.py
from rgbxy import Converter# https://github.com/benknight/hue-python-rgb-converter
from rgbxy import GamutA,GamutB,GamutC

import xbmc

from resources.lib.KodiGroup import KodiGroup
from resources.lib.KodiGroup import VIDEO,ALLMEDIA,AUDIO,STATE_IDLE,STATE_PAUSED,STATE_PLAYING


from . import kodiutils
#from .kodiutils import get_setting,get_setting_as_bool,get_setting_as_int,get_setting_as_float,convertTime
from .qhue import QhueException

import globals
from globals import logger


class AmbiGroup(KodiGroup):
    def onAVStarted(self):
        logger.info("Ambilight AV Started. Group enabled: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(self.kgroupID, self.enabled,self.isPlayingVideo(),self.isPlayingAudio(),self.mediaType,self.playbackType()))
        converter=Converter(GamutC)
        cap = xbmc.RenderCapture()
        self.state = STATE_PLAYING
        
        
        if self.enabled and self.activeTime() and self.playbackType() == 1:
        
            while not self.monitor.abortRequested() and self.state == STATE_PLAYING:
                startTime = time.time()
                cap.capture(150, 150) #async capture request to underlying OS
                capImage = cap.getImage() #timeout in ms, default 1000 
                
                image = Image.frombuffer("RGBA", (150, 150), buffer(capImage), "raw", "BGRA")
                xy=(0,0)
                
                colors = colorgram.extract(image,self.numColors)
                
                if not colors[0].rgb.r and not colors[0].rgb.g and not colors[0].rgb.b:
                    xy=converter.rgb_to_xy(1,1,1)
                else:
                    xy=converter.rgb_to_xy(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b)
                
                #self._updateHue(xy,2)
                for L in self.ambiLights: 
                    x = threading.Thread(target=self._updateHue,name="updateHue", args=(xy,L,self.transitionTime))
                    x.daemon = True
                    x.start()
        
                endTime= time.time()
                #logger.debug("xy: {}".format(xy))
                logger.debug("Colors: {}, time: {}".format(colors,endTime-startTime))
                self.monitor.waitForAbort(0.2) #seconds
            
            logger.debug("AmbiGroup stopped!")

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
        
        #self.lights=kodiutils.get_setting("group{}_Interval".format(self.kgroupID))
        self.ambiLights=map(int,kodiutils.get_setting("group{}_Lights".format(self.kgroupID)).split(","))

    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        
        super(AmbiGroup,self).setup(bridge, kgroupID, flash=flash, mediaType=1)
        
        #KodiGroup.setup(self, bridge, kgroupID, flash=flash, mediaType=mediaType)
        
        #self.enabled=True
        self.monitor=monitor
        logger.debug("AmbiGroup SetupEnd: {},{},{}".format(self.kgroupID,self.state,self))
        
        
    def _getColor(self):
        pass


    def _updateHue(self,xy,light,transitionTime):
        #startTime = time.time()
        try:
            self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
        except QhueException as e:
            logger.error("Ambi: Hue call fail: {}".format(e))
        
        #endTime=time.time()
        #logger.debug("_updateHue time: {}".format(endTime-startTime))
        
        

