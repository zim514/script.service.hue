'''
Created on Apr. 17, 2019


'''
from logging import getLogger

import xbmc
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

VIDEO=1
AUDIO=2


logger = getLogger(globals.ADDONID)


class KodiGroup(xbmc.Player):
        def __init__(self):
            super(xbmc.Player,self).__init__()

        def readSettings(self):

            self.enabled=get_setting_as_bool("group{}_enabled".format(self.kgroupID))

            self.startBehavior=get_setting_as_int("group{}_startBehavior".format(self.kgroupID))
            self.startScene=get_setting("group{}_startSceneID".format(self.kgroupID))

            self.pauseBehavior=get_setting_as_int("group{}_pauseBehavior".format(self.kgroupID))
            self.pauseScene=get_setting("group{}_pauseSceneID".format(self.kgroupID))

            self.stopBehavior=get_setting_as_int("group{}_stopBehavior".format(self.kgroupID))
            self.stopScene=get_setting("group{}_stopSceneID".format(self.kgroupID))


        def setup(self,bridge,kgroupID,flash = False, mediaType=VIDEO):
            self.bridge = bridge
            self.mediaType = mediaType

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
            logger.info("In KodiGroup[{}], onPlaybackStarted. Group enabled: {}, , isPlayingVideo: {}, isPlayingAudio: {}".format(self.kgroupID, self.enabled, self.isPlayingVideo(),self.isPlayingAudio()))

            self.state = STATE_PLAYING
            globals.lastMediaType = self.playbackType()
            if saveInitial:
                self.saveInitialState()

            if self.enabled and self.mediaType == self.playbackType() and not (globals.daylightDisable == globals.daylight) :

                if self.startBehavior == BEHAVIOR_ADJUST:
                    try:
                        self.groupResource.action(scene=self.startScene)
                    except QhueException as e:
                        logger.error("onPlaybackStopped: Hue call fail: {}".format(e))

                elif self.startBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False)


        def onPlayBackStopped(self):
            self.state = STATE_IDLE
            logger.info("In KodiGroup[{}], onPlaybackStopped() , isPlayingVideo: {}, isPlayingAudio: {} ".format(self.kgroupID,self.isPlayingVideo(),self.isPlayingAudio()))

            if self.enabled and self.mediaType == globals.lastMediaType and not (globals.daylightDisable == globals.daylight):

                if self.stopBehavior == BEHAVIOR_ADJUST:
                    try:
                        self.groupResource.action(scene=self.stopScene)
                    except QhueException as e:
                        logger.error("onPlaybackStopped: Hue call fail: {}".format(e))


                elif self.stopBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False)

                elif self.stopBehavior == BEHAVIOR_INITIAL:
                    self.applyInitialState()


        def onPlayBackPaused(self):
            self.state = STATE_PAUSED
            logger.info("In KodiGroup[{}], onPlaybackPaused() , isPlayingVideo: {}, isPlayingAudio: {}".format(self.kgroupID,self.isPlayingVideo(),self.isPlayingAudio()))

            if self.enabled and self.mediaType == self.playbackType() and not (globals.daylightDisable == globals.daylight):
                self.lastMediaType = self.playbackType()
                if self.pauseBehavior == BEHAVIOR_ADJUST:
                    try:
                        self.groupResource.action(scene=self.pauseScene)
                    except QhueException as e:
                        logger.error("onPlaybackStopped: Hue call fail: {}".format(e))

                elif self.startBehavior == BEHAVIOR_OFF:
                    self.groupResource.action(on=False)

                elif self.startBehavior == BEHAVIOR_INITIAL:
                    self.applyInitialState()
   

        def onPlayBackResumed(self):
            logger.info("In KodiGroup[{}], onPlaybackResumed()".format(self.kgroupID))
            self.onPlayBackStarted(saveInitial=False)

        def onPlayBackError(self):
            logger.info("In KodiGroup[{}], onPlaybackError()".format(self.kgroupID))
            self.onPlayBackStopped()

        def onPlayBackEnded(self):
            logger.info("In KodiGroup[{}], onPlaybackEnded()".format(self.kgroupID))
            self.onPlayBackStopped()

        def sunset(self):
            logger.info("In KodiGroup[{}], in sunset()".format(self.kgroupID))

            if self.state == STATE_PLAYING:
                self.onPlayBackStarted()
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


class KodiVideoGroup(KodiGroup):
    def __init__(self):
        super(KodiVideoGroup,self).__init__()

    def onPlayBackStarted(self, saveInitial=False):
        pass
