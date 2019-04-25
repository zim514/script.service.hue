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
            self.kgroupID=kgroupID
            self.hgroupID=hgroupID
            
            self.readSettings()
            self.group=bridge.groups[hgroupID]
            self.group()
            if kodiutils.get_setting_as_bool("initialFlash"):
                self.flash()
            
        def saveInitialState(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], save initial state".format(self.kgroupID))
            lights = self.group()["lights"]
            logger.debug("Kodi Hue: In KodiGroup, save initial state, lights: ".format(self.lights))
            a=1
            
            
        def flash(self):
            logger.debug("Kodi Hue: Flash hgroup: {}".format(self.hgroupID))
            self.group.action(alert="select")
        
        def onPlayBackStarted(self, resume=False):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackStarted".format(self.kgroupID))
            
            self.saveInitialState()

            if self.behavior is not BEHAVIOR_NOTHING:
                
                if self.startBehavior == BEHAVIOR_ADJUST:
                    if self.forceOn:
                        self.group.action(sat=self.startSaturation,hue=self.startHue,bri=self.startBrightness,transitiontime=self.fadeTime,on=True)
                    else:
                        self.group.action(sat=self.startSaturation,hue=self.startHue,bri=self.startBrightness,transitiontime=self.fadeTime)  
                        
                elif self.startBehavior == BEHAVIOR_OFF:
                    self.group.action(on=False,transitiontime=self.fadeTime)
                
            
        def onPlayBackStopped(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackStopped".format(self.kgroupID))
            
            if self.behavior is not BEHAVIOR_NOTHING:
                
                if self.stopBehavior == BEHAVIOR_ADJUST:
                    if self.forceOn:
                        self.group.action(sat=self.stopSaturation,hue=self.stopHue,bri=self.stopBrightness,transitiontime=self.fadeTime,on=True)
                    else:
                        self.group.action(sat=self.stopSaturation,hue=self.stopHue,bri=self.stopBrightness,transitiontime=self.fadeTime)  
                        
                elif self.stopBehavior == BEHAVIOR_OFF:
                    self.group.action(on=False,transitiontime=self.fadeTime)
                    
                elif self.stopBehavior == BEHAVIOR_INITIAL:
#TODO: Support inital behaviours
                    a=1

            #self.group.action(hue=0,sat=255,bri=250,transitiontime=50,on=True)
        
        def onPlayBackPaused(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackPaused".format(self.kgroupID))
            if self.behavior is not BEHAVIOR_NOTHING:
                
                if self.pauseBehavior == BEHAVIOR_ADJUST:
                    if self.forceOn:
                        self.group.action(sat=self.pauseSaturation,hue=self.pauseHue,bri=self.pauseBrightness,transitiontime=self.fadeTime,on=True)
                    else:
                        self.group.action(sat=self.pauseSaturation,hue=self.pauseHue,bri=self.pauseBrightness,transitiontime=self.fadeTime)  
                        
                elif self.startBehavior == BEHAVIOR_OFF:
                    self.group.action(on=False,transitiontime=self.fadeTime)
                    
                elif self.startBehavior == BEHAVIOR_INITIAL:
#TODO: Support inital behaviours
                    a=1            
                
        def onPlayBackResumed(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackResumed".format(self.kgroupID))
            self.onPlayBackStarted(resume=True)            
                
        def onPlayBackError(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackError".format(self.kgroupID))
            self.onPlayBackStopped()            
                
        def onPlayBackEnded(self):
            logger.debug("Kodi Hue: In KodiGroup[{}], onPlaybackEnded".format(self.kgroupID))
            self.onPlayBackStopped()
            

        

