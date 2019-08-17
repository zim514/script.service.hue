'''
Created on Apr. 17, 2019


'''
#from logging import getLogger
import datetime

import xbmc
from resources.lib.qhue import QhueException

from resources.lib import globals
from resources.lib.globals import logger
import kodiHue

#import kodiHue





STATE_IDLE = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO=1
AUDIO=2
ALLMEDIA=3

class KodiGroup(xbmc.Player):
        def __init__(self):
            super(xbmc.Player,self).__init__()

        def loadSettings(self):
            logger.debug("KodiGroup Load settings")
            self.enabled=globals.ADDON.getSettingBool("group{}_enabled".format(self.kgroupID))

            self.startBehavior=globals.ADDON.getSettingBool("group{}_startBehavior".format(self.kgroupID))
            self.startScene=globals.ADDON.getSettingString("group{}_startSceneID".format(self.kgroupID))

            self.pauseBehavior=globals.ADDON.getSettingBool("group{}_pauseBehavior".format(self.kgroupID))
            self.pauseScene=globals.ADDON.getSettingString("group{}_pauseSceneID".format(self.kgroupID))

            self.stopBehavior=globals.ADDON.getSettingBool("group{}_stopBehavior".format(self.kgroupID))
            self.stopScene=globals.ADDON.getSettingString("group{}_stopSceneID".format(self.kgroupID))


        def setup(self,bridge,kgroupID,flash = False, mediaType=VIDEO):
            if not hasattr(self,"state"):
                self.state = STATE_IDLE
            self.bridge = bridge
            self.mediaType = mediaType

            self.lights = bridge.lights
            self.kgroupID=kgroupID

            self.loadSettings()

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
            #If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
            if self.isPlayingVideo() and self.mediaType == VIDEO:
                self.videoInfoTag=self.getVideoInfoTag()
                if not self.checkVideoActivation(self.videoInfoTag):
                    return
            else:
                self.videoInfoTag = None
            globals.lastMediaType = self.playbackType()
            if self.enabled and self.checkActiveTime() and self.startBehavior and self.mediaType == self.playbackType():
                try:
                    self.state = STATE_PLAYING
                    self.groupResource.action(scene=self.startScene)
                except QhueException as e:
                    logger.error("onAVStarted: Hue call fail: {}".format(e))


        def onPlayBackStopped(self):
            logger.info("In KodiGroup[{}], onPlaybackStopped() , mediaType: {}, lastMediaType: {} ".format(self.kgroupID,self.mediaType,globals.lastMediaType))
            if self.state == STATE_PLAYING or self.state==STATE_PAUSED:
                if self.enabled and self.checkActiveTime() and self.stopBehavior and self.mediaType == globals.lastMediaType:
                    try:
                        xbmc.sleep(200) #sleep for any left over ambilight calls to complete first.
                        self.state = STATE_IDLE
                        self.groupResource.action(scene=self.stopScene)
                    except QhueException as e:
                        logger.error("onPlaybackStopped: Hue call fail: {}".format(e))


        def onPlayBackPaused(self):
            logger.info("In KodiGroup[{}], onPlaybackPaused() , isPlayingVideo: {}, isPlayingAudio: {}".format(self.kgroupID,self.isPlayingVideo(),self.isPlayingAudio()))
            if self.state == STATE_PLAYING:
                if self.enabled and self.checkActiveTime() and self.pauseBehavior and self.mediaType == self.playbackType():
                    self.lastMediaType = self.playbackType()
                    if self.mediaType == VIDEO and not self.checkVideoActivation(self.videoInfoTag):
                        return
                    try:
                        xbmc.sleep(200) #sleep for any left over ambilight calls to complete first.
                        self.state = STATE_PAUSED
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

            if self.isPlaying(): #if Kodi is playing any file, start up
                self.onAVStarted()
            elif self.state == STATE_PAUSED:
                self.onPlayBackPaused()
            else:
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
        
        
        def checkActiveTime(self):
            logger.debug("in checkActiveTime. Schedule: {}".format(globals.enableSchedule))
            
            if globals.daylightDisable and globals.daylight:
                logger.debug("Disabled by daylight")
                return False

            if globals.enableSchedule: 
                start=kodiHue.convertTime(globals.startTime)
                end=kodiHue.convertTime(globals.endTime)
                now=datetime.datetime.now().time()
                if (now > start) and (now <end):
                    logger.debug("Schedule active")
                    return True
                logger.debug("Disabled by schedule time")
                return False
            logger.debug("Schedule not enabled, ignoring")
            return True


        def checkVideoActivation(self,infoTag):
            if self.isPlayingVideo():
                duration=infoTag.getDuration() / 60 #returns seconds, convert to minutes
                mediaType=infoTag.getMediaType()
                logger.debug("Video Activation settings({}): minDuration: {}, Movie: {}, Episode: {}, MusicVideo: {}, Other: {}".
                             format(self.kgroupID,globals.videoMinimumDuration,globals.video_enableMovie,globals.video_enableEpisode,globals.video_enableMusicVideo,globals.video_enableOther))
                logger.debug("Video Activation ({}): Duration: {}, mediaType: {}".format(self.kgroupID,duration,mediaType))
                if duration > globals.videoMinimumDuration and \
                    ((globals.video_enableMovie and mediaType == "movie") or
                    (globals.video_enableEpisode and mediaType == "episode") or 
                    (globals.video_enableMusicVideo and mediaType == "MusicVideo") or 
                    globals.video_enableOther):
                    logger.debug("Video activation: True")
                    return True
            logger.debug("Video activation: False")
            return False

