'''
Created on Jul. 2, 2019

@author: Zim514
'''

import time
from threading import Thread
 #https://realpython.com/intro-to-python-threading/#daemon-threads 
#from threading import Timer


from PIL import Image
from . import colorgram #https://github.com/obskyr/colorgram.py
from .rgbxy import Converter# https://github.com/benknight/hue-python-rgb-converter
from .rgbxy import ColorHelper
from .rgbxy import XYPoint
from .rgbxy import GamutA,GamutB,GamutC

import xbmc

from resources.lib.KodiGroup import KodiGroup
from resources.lib.KodiGroup import VIDEO,AUDIO,ALLMEDIA,STATE_IDLE,STATE_PAUSED,STATE_PLAYING


from . import kodiutils
#from .kodiutils import get_setting,get_setting_as_bool,get_setting_as_int,get_setting_as_float,convertTime
from .qhue import QhueException

from . import globals
from .globals import logger
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
        self.blackFilter=kodiutils.get_setting_as_int("group{}_BlackFilter".format(self.kgroupID))
        self.whiteFilter=kodiutils.get_setting_as_int("group{}_WhiteFilter".format(self.kgroupID))
        
        
        
        #self.lights=kodiutils.get_setting("group{}_Interval".format(self.kgroupID))
        self.ambiLights={}
        lightIDs=kodiutils.get_setting("group{}_Lights".format(self.kgroupID)).split(",")
        for L in lightIDs:

            gamut=self._getLightGamut(self.bridge,L)
            light={L:{'gamut': gamut,'prevxy': (0,0)}}
            self.ambiLights.update(light)
            

        #read gamuts, make this a dict
        logger.debug("ambilights obj: {}".format(self.ambiLights))
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        
        super(AmbiGroup,self).setup(bridge, kgroupID, flash=flash, mediaType=1)
        
        self.monitor=monitor

        calls=1/(self.updateInterval)*len(self.ambiLights)  #updateInterval is in seconds, eg. 0.2 for 200ms.  
        logger.debug("callsPerSec: lights: {},interval: {}, calls: {}".format(len(self.ambiLights),self.updateInterval,calls))
        kodiutils.notification(_("Hue Service"), _("Est. Hue Calls/sec (max 10): {}").format(calls),time=10000)

    
    def _getColor(self):
        pass

    def _ambiLoop(self):
        
        cap = xbmc.RenderCapture()
        
        
        distance=0.0
        self.xy=0.5266,0.4133
        self.prevxy=0.5266,0.4133
        logger.debug("AmbiGroup started!")
        
        while not self.monitor.abortRequested() and self.state == STATE_PLAYING:
            startTime = time.time()
             
            try:
                cap.capture(250, 250) #async capture request to underlying OS
                capImage = cap.getImage() #timeout to wait for OS in ms, default 1000
                image = Image.frombuffer("RGBA", (250, 250), buffer(capImage), "raw", "BGRA")
            except Exception:
                return #avoid fails in system shutdown
                
            
            
            colors = colorgram.extract(image,self.numColors)
            #TODO: RGB min and max configurable.
            if (colors[0].rgb.r < self.blackFilter and colors[0].rgb.g < self.blackFilter and colors[0].rgb.b <self.blackFilter) or \
            (colors[0].rgb.r > self.whiteFilter and colors[0].rgb.g > self.whiteFilter and colors[0].rgb.b > self.whiteFilter):
                logger.debug("rgb filter: r,g,b: {},{},{}".format(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b))
                
                xy=0.5266,0.4133 #default
                
                for L in self.ambiLights: 
                    x = Thread(target=self._updateHueXY,name="updateHue", args=(xy,L,self.transitionTime))
                    x.daemon = True
                    x.start()
                
            else:
                for L in self.ambiLights: 
                    x = Thread(target=self._updateHueRGB,name="updateHue", args=(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b,L,self.transitionTime))
                    x.daemon = True
                    x.start()
            
            endTime= time.time()

            self.monitor.waitForAbort(self.updateInterval) #seconds

        logger.debug("AmbiGroup stopped!")
        
        
        
    
    def _updateHueRGB(self,r,g,b,light,transitionTime):
        startTime = time.time()
        
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
        xy=(round(xy[0],4),round(xy[1],4)) #Hue has a max precision of 4 decimal points.

        distance=round(helper.get_distance_between_two_points(XYPoint(xy[0],xy[1]),XYPoint(prevxy[0],prevxy[1])) ,4)#only update hue if XY actually changed
        if distance > 0:
            try:
                self.bridge.lights[light].state(xy=xy,transitiontime=transitionTime)
            except QhueException as e:
                logger.error("Ambi: Hue call fail: {}".format(e))
        
        #=======================================================================
        endTime=time.time()
        # 
        # 
        
        #logger.debug("_updateHue time: {}".format(int((endTime-startTime)*1000)))
        
        logger.debug("time: {},distance: {}".format(int((endTime-startTime)*1000),distance))
        # if distance > 0:
        #     #logger.debug("time: {},Colors: {}, xy: {},prevxy:{}, distance: {}".format(endTime-startTime,colors,xy,prevxy,distance))
        #     #logger.debug("***** xy: {},prevxy:{}, distance: {}".format(xy,prevxy,distance))
        #     pass
        # else:
        #     #logger.debug("* xy: {},prevxy:{}, distance: {}".format(xy,prevxy,distance))
        #     pass
        #  
        # 
        # 
        #=======================================================================
        self.ambiLights[light].update(prevxy=xy)
        

    def _updateHueXY(self,xy,light,transitionTime):
        startTime = time.time()
        
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
            except QhueException as e:
                logger.error("Ambi: Hue call fail: {}".format(e))
        
        #=======================================================================
        endTime=time.time()
        # 
        # 
        
        #logger.debug("_updateHue time: {}".format(int((endTime-startTime)*1000)))
        
        logger.debug("time: {},distance: {}".format(int((endTime-startTime)*1000),distance))
        # if distance > 0:
        #     #logger.debug("time: {},Colors: {}, xy: {},prevxy:{}, distance: {}".format(endTime-startTime,colors,xy,prevxy,distance))
        #     #logger.debug("***** xy: {},prevxy:{}, distance: {}".format(xy,prevxy,distance))
        #     pass
        # else:
        #     #logger.debug("* xy: {},prevxy:{}, distance: {}".format(xy,prevxy,distance))
        #     pass
        #  
        # 
        # 
        #=======================================================================
        self.ambiLights[light].update(prevxy=xy)




    def _getLightGamut(self,bridge,L):
        try:
            gamut = bridge.lights()[L]['capabilities']['control']['colorgamuttype']
            logger.debug("Light: {}, gamut: {}".format(L,gamut))
        except Exception:
            return None
        if gamut == "A"  or gamut == "B" or gamut == "C":
            return gamut
        return None
        


