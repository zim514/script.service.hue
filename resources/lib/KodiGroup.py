'''
Created on Apr. 17, 2019

@author: Kris
'''
import xbmc
import qhue
import logging
import xbmcaddon
import kodiutils
import globals

from kodiutils import get_setting, get_setting_as_bool, get_setting_as_int


BEHAVIOR_NOTHING = 0
BEHAVIOR_ADJUST = 1
BEHAVIOR_OFF = 2
BEHAVIOR_INITIAL = 3

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))


class KodiGroup(xbmc.Player):
        def __init__(self):
            super(xbmc.Player,self).__init__()

        def readSettings(self):
          
            self.behavior=get_setting("group{}_behavior".format(self.kgroupID))
            self.fadeTime=get_setting_as_int("group{}_fadeTime".format(self.kgroupID))*10 #Stored as seconds, but Hue API expects multiples of 100ms.
            self.forceOn=get_setting_as_bool("group{}_forceOn".format(self.kgroupID))
            
            #Hue API values start at 0, but settings UI starts at 1 for usability. -1 on XML values for 'conversion'
            self.startBehavior=get_setting_as_int("group{}_startBehavior".format(self.kgroupID))
            self.startHue=get_setting_as_int("group{}_startHue".format(self.kgroupID)) - 1
            self.startSaturation=get_setting_as_int("group{}_startSaturation".format(self.kgroupID)) - 1
            self.startBrightness=get_setting_as_int("group{}_startBrightness".format(self.kgroupID)) - 1
            
            self.pauseBehavior=get_setting_as_int("group{}_pauseBehavior".format(self.kgroupID))
            self.pauseHue=get_setting_as_int("group{}_pauseHue".format(self.kgroupID)) -1
            self.pauseSaturation=get_setting_as_int("group{}_pauseSaturation".format(self.kgroupID)) -1
            self.pauseBrightness=get_setting_as_int("group{}_pauseBrightness".format(self.kgroupID)) -1
            
            self.stopBehavior=get_setting_as_int("group{}_stopBehavior".format(self.kgroupID))
            self.stopHue=get_setting_as_int("group{}_stopHue".format(self.kgroupID)) -1
            self.stopSaturation=get_setting_as_int("group{}_stopSaturation".format(self.kgroupID)) -1
            self.stopBrightness=get_setting_as_int("group{}_stopBrightness".format(self.kgroupID)) -1

            
        def setup(self,bridge,kgroupID,hgroupID):
            self.bridge = bridge
            
            self.lights = bridge.lights 
            self.kgroupID=kgroupID
            self.hgroupID=hgroupID
            self.groupResource=bridge.groups[self.hgroupID]
            self.lightIDs=self.groupResource()["lights"]
            
            self.saveInitialState()
            self.readSettings()
            
            #self.group = groupResource()
            if kodiutils.get_setting_as_bool("kgroup0_initialFlash"):
                self.flash()
            
        def saveInitialState(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], save initial state".format(self.kgroupID))
            initialState = {}
            lights = self.lights
                        
            for x in self.lightIDs:
                light=lights[x]()
                initialState[x] = light['state'] 
                #self.initialState.append(lights.l()['state'])

            self.initialState=initialState
             
            
        def applyInitialState(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], apply initial state".format(self.kgroupID))
            initialState = self.initialState
            lights = self.lights 
            
            for x in initialState:
                i = initialState[x]
                logger.debug("Kodi Hue: In KodiGroup[{}], apply initial state: {}, {}".format(self.kgroupID,x,i))
                lights[x].state(on=i['on'],
                                ct=i['ct'],
                                xy=i['xy'],
                                bri=i['bri'],
                                hue=i['hue'],
                                sat=i['sat'],
                                transitiontime=self.fadeTime)
                
                                
                
            
            logger.debug("Kodi Hue: In KodiGroup[{}], apply initial state ENDDDDD".format(self.kgroupID))    
 
            
        def flash(self):
            logger.debug("Kodi Hue: Flash hgroup: {}".format(self.hgroupID))
            self.groupResource.action(alert="select")
        
        def onPlayBackStarted(self, resume=False):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackStarted. Group behavior: {}, forceOn: {}".format(self.kgroupID, self.behavior, self.forceOn))
            
            self.saveInitialState()

            if self.behavior is not BEHAVIOR_NOTHING:
                
                if self.startBehavior == BEHAVIOR_ADJUST:
                    if self.forceOn:
                        self.groupResource.action(sat=self.startSaturation,hue=self.startHue,bri=self.startBrightness,transitiontime=self.fadeTime,on=True)
                    else:
                        self.groupResource.action(sat=self.startSaturation,hue=self.startHue,bri=self.startBrightness,transitiontime=self.fadeTime)  
                        
                elif self.startBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False,transitiontime=self.fadeTime)
                
            
        def onPlayBackStopped(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackStopped".format(self.kgroupID))
            
            if self.behavior is not BEHAVIOR_NOTHING:
                
                if self.stopBehavior == BEHAVIOR_ADJUST:
                    if self.forceOn:
                        self.groupResource.action(sat=self.stopSaturation,hue=self.stopHue,bri=self.stopBrightness,transitiontime=self.fadeTime,on=True)
                    else:
                        self.groupResource.action(sat=self.stopSaturation,hue=self.stopHue,bri=self.stopBrightness,transitiontime=self.fadeTime)  
                        
                elif self.stopBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False,transitiontime=self.fadeTime)
                    
                elif self.stopBehavior == BEHAVIOR_INITIAL:
                    self.applyInitialState()
            
        
        def onPlayBackPaused(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackPaused".format(self.kgroupID))
            if self.behavior is not BEHAVIOR_NOTHING:
                
                if self.pauseBehavior == BEHAVIOR_ADJUST:
                    if self.forceOn:
                        self.groupResource.action(sat=self.pauseSaturation,hue=self.pauseHue,bri=self.pauseBrightness,transitiontime=self.fadeTime,on=True)
                    else:
                        self.groupResource.action(sat=self.pauseSaturation,hue=self.pauseHue,bri=self.pauseBrightness,transitiontime=self.fadeTime)  
                        
                elif self.startBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False,transitiontime=self.fadeTime)
                    
                elif self.startBehavior == BEHAVIOR_INITIAL:
                    self.applyInitialState()
   
                
        def onPlayBackResumed(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackResumed".format(self.kgroupID))
            self.onPlayBackStarted(resume=True)            
                
        def onPlayBackError(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackError".format(self.kgroupID))
            self.onPlayBackStopped()            
                
        def onPlayBackEnded(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackEnded".format(self.kgroupID))
            self.onPlayBackStopped()
            

        

