'''
Created on Apr. 17, 2019


'''
import logging

import xbmc
import xbmcaddon

from . import globals
from .kodiutils import get_setting, get_setting_as_bool, get_setting_as_int
from .qhue import QhueException


BEHAVIOR_NOTHING = 0
BEHAVIOR_ADJUST = 1
BEHAVIOR_OFF = 2
BEHAVIOR_INITIAL = 3

STATE_IDLE = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

state = 0

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(__name__)


class KodiGroup(xbmc.Player):
        def __init__(self):
            super(xbmc.Player,self).__init__()

        def readSettings(self):
          
            self.enabled=get_setting_as_bool("group{}_enabled".format(self.kgroupID))
            self.fadeTime=get_setting_as_int("group{}_fadeTime".format(self.kgroupID)) * 10 #Stored as seconds, but Hue API expects multiples of 100ms.
            self.forceOn=get_setting_as_bool("group{}_forceOn".format(self.kgroupID))
            
            
            self.startBehavior=get_setting_as_int("group{}_startBehavior".format(self.kgroupID))
            self.startScene=get_setting("group{}_startSceneID".format(self.kgroupID))
            
            self.pauseBehavior=get_setting_as_int("group{}_pauseBehavior".format(self.kgroupID))
            self.pauseScene=get_setting("group{}_pauseSceneID".format(self.kgroupID))
            
            self.stopBehavior=get_setting_as_int("group{}_stopBehavior".format(self.kgroupID))
            self.stopScene=get_setting("group{}_stopSceneID".format(self.kgroupID))
            
            
        def setup(self,bridge,kgroupID,flash = False):
            self.bridge = bridge
            
            
            self.lights = bridge.lights 
            self.kgroupID=kgroupID
            
            self.readSettings()
            
            self.groupResource=bridge.groups[0]
            #TODO: Get scene lights to save initial state
            self.lightIDs=self.groupResource()["lights"]
            self.saveInitialState()

            if flash:
                self.flash()
                    
                    
                
        def saveInitialState(self):
            #TODO: Get scene lights to save initial state
            logger.debug("In KodiGroup[{}], save initial state".format(self.kgroupID))
            initialState = {}
            lights = self.lights
                        
            for x in self.lightIDs:
                light=lights[x]()
                initialState[x] = light['state'] 
                #self.initialState.append(lights.l()['state'])

            self.initialState=initialState
             
            
        def applyInitialState(self):
            logger.debug("In KodiGroup[{}], apply initial state".format(self.kgroupID))
            initialState = self.initialState
            lights = self.lights 
            
            for x in initialState:
                i = initialState[x]
                logger.debug("In KodiGroup[{}], apply initial state: {}, {}".format(self.kgroupID,x,i))
                lights[x].state(on=i['on'],
                                ct=i['ct'],
                                xy=i['xy'],
                                bri=i['bri'],
                                hue=i['hue'],
                                sat=i['sat'],
                                transitiontime=self.fadeTime)
            
        def flash(self):
            logger.debug("in KodiGroup Flash")
            self.groupResource.action(alert="select")
        
        def onPlayBackStarted(self, saveInitial=False):
            logger.debug("In KodiGroup[{}], onPlaybackStarted. Group enabled: {}, forceOn: {}".format(self.kgroupID, self.enabled, self.forceOn))
            self.state = STATE_PLAYING
            if saveInitial:
                self.saveInitialState()

            if self.enabled and not (globals.daylightDisable == globals.daylight) :
                
                if self.startBehavior == BEHAVIOR_ADJUST:
                    try:
                        self.groupResource.action(scene=self.startScene)
                    except QhueException as e:
                        logger.debug("onPlaybackStopped: Hue call fail: {}".format(e))  
                        
                elif self.startBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False)
                
            
        def onPlayBackStopped(self):
            self.state = STATE_IDLE
            logger.debug("In KodiGroup[{}], onPlaybackStopped() ".format(self.kgroupID))
            
            if self.enabled and not (globals.daylightDisable == globals.daylight):
                
                if self.stopBehavior == BEHAVIOR_ADJUST:
                    try:
                        self.groupResource.action(scene=self.stopScene)
                    except QhueException as e:
                        logger.debug("onPlaybackStopped: Hue call fail: {}".format(e))
                            
                        
                elif self.stopBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False)
                    
                elif self.stopBehavior == BEHAVIOR_INITIAL:
                    self.applyInitialState()
            
        
        def onPlayBackPaused(self):
            self.state = STATE_PAUSED
            logger.debug("In KodiGroup[{}], onPlaybackPaused()".format(self.kgroupID))
            
            if self.enabled and not (globals.daylightDisable == globals.daylight):
                
                if self.pauseBehavior == BEHAVIOR_ADJUST:
                    try:
                        self.groupResource.action(scene=self.pauseScene)
                    except QhueException as e:
                        logger.debug("onPlaybackStopped: Hue call fail: {}".format(e))  
                        
                elif self.startBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False)
                    
                elif self.startBehavior == BEHAVIOR_INITIAL:
                    self.applyInitialState()
   
                
        def onPlayBackResumed(self):
            logger.debug("In KodiGroup[{}], onPlaybackResumed()".format(self.kgroupID))
            self.onPlayBackStarted(saveInitial=False)            
                
        def onPlayBackError(self):
            logger.debug("In KodiGroup[{}], onPlaybackError()".format(self.kgroupID))
            self.onPlayBackStopped()            
                
        def onPlayBackEnded(self):
            logger.debug("In KodiGroup[{}], onPlaybackEnded()".format(self.kgroupID))
            self.onPlayBackStopped()
            
        def sunset(self):
            logger.debug("In KodiGroup[{}], in sunset()".format(self.kgroupID))
            previousForce = self.forceOn
            self.forceOn = True
            
            if self.state == STATE_PLAYING:
                self.onPlayBackStarted()
            elif self.state == STATE_PAUSED:
                self.onPlayBackPaused()
            elif self.state == STATE_IDLE:
                self.onPlayBackStopped()
                
            self.forceOn = previousForce
                
                
        

