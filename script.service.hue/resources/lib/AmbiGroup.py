'''
Created on Jul. 2, 2019

@author: Zim514
'''
import io
import time
import colorsys
 
from PIL import Image
import colorgram

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
        
        
        
        cap = xbmc.RenderCapture()
        while not self.monitor.abortRequested():
        #monitor.waitForAbort(1)
        
            startTime = time.time()
            cap.capture(150, 150) #async capture request to underlying OS
            capImage = cap.getImage() #timeout in ms, default 1000 
            
            image = Image.frombuffer("RGBA", (150, 150), buffer(capImage), "raw", "BGRA")
            
            
            colors = colorgram.extract(image,1)
            hsv=rgbToHSV(colors[0].rgb.r,colors[0].rgb.g,colors[0].rgb.b)
            #colorsys.rgb_to_hsv(colorsp[])
            self.bridge.lights[5].state(hue=hsv[0], sat=hsv[1], bri=hsv[2])
            #HSV values are 0-1
            endTime= time.time()
            logger.debug("hsv: {}".format(hsv))
            logger.debug("Colors: {}, time: {}".format(colors,endTime-startTime))
            self.monitor.waitForAbort(2) #seconds
        
    
    def readSettings(self):
        #KodiGroup.readSettings(self)
        
        pass
    
    
    def setup(self, monitor,bridge, kgroupID, flash=False, mediaType=VIDEO):
        KodiGroup.setup(self, bridge, kgroupID, flash=flash, mediaType=mediaType)
        
        self.enabled=True
        self.monitor=monitor
        
        

def rgbToHSV(r, g, b):
    #
    """Convert RGB color space to HSV color space
    
    @param r: Red
    @param g: Green
    @param b: Blue
    return (h, s, v)  
    """
    maxc = max(r, g, b)
    minc = min(r, g, b)
    colorMap = {
        id(r): 'r',
        id(g): 'g',
        id(b): 'b'
    }
    if colorMap[id(maxc)] == colorMap[id(minc)]:
        h = 0
    elif colorMap[id(maxc)] == 'r':
        h = 60.0 * ((g - b) / (maxc - minc)) % 360.0
    elif colorMap[id(maxc)] == 'g':
        h = 60.0 * ((b - r) / (maxc - minc)) + 120.0
    elif colorMap[id(maxc)] == 'b':
        h = 60.0 * ((r - g) / (maxc - minc)) + 240.0
    v = maxc
    if maxc == 0.0:
        s = 0.0
    else:
        s = 1.0 - (minc / maxc)
    return (h, s, v)