'''
Created on Apr. 17, 2019


'''
#from logging import getLogger
import datetime


import xbmc
from . import globals
from globals import logger

from .kodiutils import get_setting, get_setting_as_bool,convertTime
from .qhue import QhueException

#BEHAVIOR_NOTHING = 0
#BEHAVIOR_ADJUST = 1
#BEHAVIOR_OFF = 2
#BEHAVIOR_INITIAL = 3

STATE_IDLE = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO=1
AUDIO=2
ALLMEDIA=3


#logger = getLogger(globals.ADDONID)


class KodiGroup(xbmc.Player):
        def __init__(self):
            super(xbmc.Player,self).__init__()

        def readSettings(self):

            self.enabled=get_setting_as_bool("group{}_enabled".format(self.kgroupID))

            self.startBehavior=get_setting_as_bool("group{}_startBehavior".format(self.kgroupID))
            self.startScene=get_setting("group{}_startSceneID".format(self.kgroupID))

            self.pauseBehavior=get_setting_as_bool("group{}_pauseBehavior".format(self.kgroupID))
            self.pauseScene=get_setting("group{}_pauseSceneID".format(self.kgroupID))

            self.stopBehavior=get_setting_as_bool("group{}_stopBehavior".format(self.kgroupID))
            self.stopScene=get_setting("group{}_stopSceneID".format(self.kgroupID))


        def setup(self,bridge,kgroupID,flash = False, mediaType=VIDEO):
            if not hasattr(self,"state"):
                self.state = STATE_IDLE
            self.bridge = bridge
            self.mediaType = mediaType

            self.lights = bridge.lights
            self.kgroupID=kgroupID

            self.readSettings()

            self.groupResource=bridge.groups[0]

            if flash:
                self.flash()


        def flash(self):
            logger.debug("in KodiGroup Flash")
            try:
                self.groupResource.action(alert="select")
            except QhueException() as e:
                logger.error("Hue Error: {}".format(e))


        def onAVStarted(self):
            logger.info("In KodiGroup[{}], onPlaybackStarted. Group enabled: {},startBehavior: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(self.kgroupID, self.enabled,self.startBehavior, self.isPlayingVideo(),self.isPlayingAudio(),self.mediaType,self.playbackType()))
            
            self.state = STATE_PLAYING
            globals.lastMediaType = self.playbackType()
            
            if self.enabled and self.activeTime() and self.startBehavior and self.mediaType == self.playbackType():

                try:
                    self.groupResource.action(scene=self.startScene)
                except QhueException as e:
                    logger.error("onPlaybackStopped: Hue call fail: {}".format(e))


        def onPlayBackStopped(self):
            logger.info("In KodiGroup[{}], onPlaybackStopped() , mediaType: {}, lastMediaType: {} ".format(self.kgroupID,self.mediaType,globals.lastMediaType))
            self.state = STATE_IDLE
            if self.enabled and self.activeTime() and self.stopBehavior and self.mediaType == globals.lastMediaType:
                try:
                    self.groupResource.action(scene=self.stopScene)
                except QhueException as e:
                    logger.error("onPlaybackStopped: Hue call fail: {}".format(e))

        def onPlayBackPaused(self):
            logger.info("In KodiGroup[{}], onPlaybackPaused() , isPlayingVideo: {}, isPlayingAudio: {}".format(self.kgroupID,self.isPlayingVideo(),self.isPlayingAudio()))
            self.state = STATE_PAUSED
            if self.enabled and self.activeTime() and self.pauseBehavior and self.mediaType == self.playbackType():
                self.lastMediaType = self.playbackType()
                try:
                    self.groupResource.action(scene=self.pauseScene)
                except QhueException as e:
                    logger.error("onPlaybackStopped: Hue call fail: {}".format(e))


        def onPlayBackResumed(self):
            logger.info("In KodiGroup[{}], onPlaybackResumed()".format(self.kgroupID))
            self.onAVStarted()

        def onPlayBackError(self):
            logger.info("In KodiGroup[{}], onPlaybackError()".format(self.kgroupID))
            self.onPlayBackStopped()

        def onPlayBackEnded(self):
            logger.info("In KodiGroup[{}], onPlaybackEnded()".format(self.kgroupID))
            self.onPlayBackStopped()

        def sunset(self):
            logger.info("In KodiGroup[{}], in sunset()".format(self.kgroupID))

            if self.state == STATE_PLAYING:
                self.onAVStarted()
            elif self.state == STATE_PAUSED:
                self.onPlayBackPaused()
            elif self.state == STATE_IDLE:
                #self.onPlayBackStopped()
                #if not playing and sunset happens, probably should do nothing.
                logger.debug("In KodiGroup[{}], in sunset(). playback stopped, doing nothing. ".format(self.kgroupID))

        def playbackType(self):
            if self.isPlayingVideo():
                mediaType=VIDEO
            elif self.isPlayingAudio():
                mediaType=AUDIO
            else:
                mediaType=None
            return mediaType
        
        
        def activeTime(self):

            if globals.daylightDisable and globals.daylight:
                logger.debug("Disabled by daylight")
                return False

            if globals.enableSchedule is False:
                return True

            start=convertTime(globals.startTime)
            end=convertTime(globals.endTime)
            now = datetime.datetime.now().time()
            
            logger.debug("Schedule check: start: {}, now: {}, end: {}".format(start,now,end))

            if (now > start) and (now <end):
                logger.debug("Schedule active")
                return True
            logger.debug("Disabled by schedule")
            return False


#===============================================================================
#         def _saveInitialState(self):
#             #TODO: Get scene lights to save initial state
#             #This method no longer works
#             logger.debug("In KodiGroup[{}], save initial state".format(self.kgroupID))
#             initialState = {}
#             lights = self.lights
#
#             for x in self.lightIDs:
#                 light=lights[x]()
#                 initialState[x] = light['state']
#                 #self.initialState.append(lights.l()['state'])
#
#             self.initialState=initialState
#
#         def _applyInitialState(self):
#             #Deprecated with new scene support
#             logger.debug("In KodiGroup[{}], apply initial state".format(self.kgroupID))
#             initialState = self.initialState
#             lights = self.lights
#
#             for x in initialState:
#                 i = initialState[x]
#                 logger.debug("In KodiGroup[{}], apply initial state: {}, {}".format(self.kgroupID,x,i))
#                 lights[x].state(on=i['on'],
#                                 ct=i['ct'],
#                                 xy=i['xy'],
#                                 bri=i['bri'],
#                                 hue=i['hue'],
#                                 sat=i['sat'],
#                                 transitiontime=self.fadeTime)
#===============================================================================
