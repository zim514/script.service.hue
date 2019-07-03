'''
Created on Jul. 2, 2019

@author: Zim514
'''
import io
import time


from PIL import Image
import colorgram #https://github.com/obskyr/colorgram.py
from rgbxy import Converter# https://github.com/benknight/hue-python-rgb-converter
from rgbxy import GamutA,GamutB,GamutC

import xbmc

from resources.lib.KodiGroup import KodiGroup
from resources.lib.KodiGroup import VIDEO,ALLMEDIA,AUDIO,STATE_IDLE,STATE_PAUSED,STATE_PLAYING

from .kodiutils import get_setting,get_setting_as_bool,convertTime
from .qhue import QhueException

import globals
from globals import logger


class AmbiGroup(KodiGroup):
    '''
    classdocs
    '''

    #===========================================================================
    # def __init__(self, params):
    #     '''
    #     Constructor
    #     '''
    # super(KodiGroup).__init__()
    #===========================================================================
    
    
    def onAVStarted(self):
        logger.debug("AmbiGroup Start!")
        
        converter=Converter(GamutC)
        cap = xbmc.RenderCapture()
        
        while not self.monitor.abortRequested():
        #monitor.waitForAbort(1)
        
            startTime = time.time()
            cap.capture(150, 150) #async capture request to underlying OS
            capImage = cap.getImage() #timeout in ms, default 1000 
            
            image = Image.frombuffer("RGBA", (150, 150), buffer(capImage), "raw", "BGRA")
            xy=(0,0)
            
            colors = colorgram.extract(image,1)
            
            if not colors[0].rgb.r and not colors[0].rgb.g and not colors[0].rgb.b:
                xy=converter.rgb_to_xy(1,1,1)
            else:
                xy=converter.rgb_to_xy(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b)
            self.bridge.lights[5].state(xy=xy,transitiontime=2)
                
            endTime= time.time()
            #logger.debug("xy: {}".format(xy))
            logger.debug("Colors: {}, time: {}".format(colors,endTime-startTime))
            self.monitor.waitForAbort(0.2) #seconds
        
    
    def readSettings(self):
        #KodiGroup.readSettings(self)
        
        pass
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        KodiGroup.setup(self, bridge, kgroupID, flash=flash, mediaType=mediaType)
        
        self.enabled=True
        self.monitor=monitor
        
        
