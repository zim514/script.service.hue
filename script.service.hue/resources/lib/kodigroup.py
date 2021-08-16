import datetime

import requests
import xbmc
import xbmcgui

from resources.lib import CACHE, reporting, kodihue
from resources.lib.kodisettings import convert_time
from resources.lib.qhue import QhueException
from . import ADDON
from .kodisettings import settings_storage
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 1
AUDIO = 2
ALL_MEDIA = 3


class KodiGroup(xbmc.Player):
    def __init__(self, kgroupID, bridge, mediaType, flash=False):
        # xbmc.log("[script.service.hue] KodiGroup Load settings for group: {}".format(kgroupID))
        self.kgroupID = kgroupID
        self.bridge = bridge
        self.enabled = ADDON.getSettingBool("group{}_enabled".format(self.kgroupID))

        self.startBehavior = ADDON.getSettingBool("group{}_startBehavior".format(self.kgroupID))
        self.startScene = ADDON.getSettingString("group{}_startSceneID".format(self.kgroupID))

        self.pauseBehavior = ADDON.getSettingBool("group{}_pauseBehavior".format(self.kgroupID))
        self.pauseScene = ADDON.getSettingString("group{}_pauseSceneID".format(self.kgroupID))

        self.stopBehavior = ADDON.getSettingBool("group{}_stopBehavior".format(self.kgroupID))
        self.stopScene = ADDON.getSettingString("group{}_stopSceneID".format(self.kgroupID))

        self.state = STATE_STOPPED

        self.mediaType = mediaType
        self.lights = self.bridge.lights
        self.group0 = self.bridge.groups[0]

        if flash:
            self.flash()

        super().__init__()

    def __repr__(self):
        return "kgroupID: {}, enabled: {}, startBehavior: {}, startScene: {}, pauseBehavior: {}, pauseScene:{}, stopBehavior: {}, stopScene:{}, state: {}, mediaType: {}".format(self.kgroupID, self.enabled, self.startBehavior,
                                                                                                                                                                                 self.startScene, self.pauseScene, self.pauseScene,
                                                                                                                                                                                 self.stopBehavior, self.stopScene, self.state, self.mediaType)

    def flash(self):
        # xbmc.log("[script.service.hue] in KodiGroup Flash")
        try:
            self.group0.action(alert="select")
        except QhueException as exc:
            xbmc.log("[script.service.hue] Hue call fail: {}: {}".format(exc.type_id, exc.message))
            reporting.process_exception(exc)
        except requests.RequestException as exc:
            xbmc.log("[script.service.hue] RequestException: {}".format(exc))

    def onAVStarted(self):
        if self.enabled:
            xbmc.log(
                "In KodiGroup[{}], onPlaybackStarted. Group enabled: {},startBehavior: {} , isPlayingVideo: {}, isPlayingAudio: {}, self.mediaType: {},self.playbackType(): {}".format(
                    self.kgroupID, self.enabled, self.startBehavior, self.isPlayingVideo(), self.isPlayingAudio(),
                    self.mediaType, self.playback_type()))
            self.state = STATE_PLAYING
            settings_storage['lastMediaType'] = self.playback_type()

            if self.isPlayingVideo() and self.mediaType == VIDEO:  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                try:
                    self.videoInfoTag = self.getVideoInfoTag()
                except Exception as exc:
                    xbmc.log("[script.service.hue] Get InfoTag Exception: {}".format(exc))
                    reporting.process_exception(exc)
                    return
                # xbmc.log("[script.service.hue] InfoTag: {}".format(self.videoInfoTag))
                if not self.check_video_activation(self.videoInfoTag):
                    return
            else:
                self.videoInfoTag = None

            if (self.check_active_time() or self.check_already_active(self.startScene)) and self.check_keep_lights_off_rule(self.startScene) and self.startBehavior and self.mediaType == self.playback_type():
                self.run_play()

    def onPlayBackStopped(self):
        if self.enabled:
            xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackStopped() , mediaType: {}, lastMediaType: {} ".format(self.kgroupID, self.mediaType, settings_storage['lastMediaType']))
            self.state = STATE_STOPPED

            try:
                if self.mediaType == VIDEO and not self.check_video_activation(
                        self.videoInfoTag):  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                    return
            except AttributeError:
                xbmc.log("[script.service.hue] No videoInfoTag")

            if (self.check_active_time() or self.check_already_active(self.stopScene)) and self.check_keep_lights_off_rule(self.stopScene) and self.stopBehavior and self.mediaType == settings_storage['lastMediaType']:
                self.run_stop()

    def onPlayBackPaused(self):
        if self.enabled:
            xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackPaused() , isPlayingVideo: {}, isPlayingAudio: {}".format(self.kgroupID, self.isPlayingVideo(), self.isPlayingAudio()))
            self.state = STATE_PAUSED

            if self.mediaType == VIDEO and not self.check_video_activation(
                    self.videoInfoTag):  # If video group, check video activation. Otherwise it's audio so we ignore this and continue
                return

            if (self.check_active_time() or self.check_already_active(self.pauseScene)) and self.check_keep_lights_off_rule(self.pauseScene) and self.pauseBehavior and self.mediaType == self.playback_type():
                settings_storage['lastMediaType'] = self.playback_type()
                self.run_pause()

    def onPlayBackResumed(self):
        # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackResumed()".format(self.kgroupID))
        self.onAVStarted()

    def onPlayBackError(self):
        # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackError()".format(self.kgroupID))
        self.onPlayBackStopped()

    def onPlayBackEnded(self):
        # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackEnded()".format(self.kgroupID))
        self.onPlayBackStopped()

    def run_play(self):
        try:
            self.group0.action(scene=self.startScene)
        except QhueException as exc:
            xbmc.log("[script.service.hue] onAVStarted: Hue call fail: {}: {}".format(exc.type_id, exc.message))
            if exc.type_id == 7:
                xbmc.log("[script.service.hue] Scene not found")
                kodihue.notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(exc)

    def run_pause(self):
        try:
            xbmc.sleep(500)  # sleep for any left over ambilight calls to complete first.
            self.group0.action(scene=self.pauseScene)
            # xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackPaused() Pause scene activated")
        except QhueException as exc:
            xbmc.log("[script.service.hue] run_pause Hue call fail: {}: {}".format(exc.type_id, exc.message))
            if exc.type_id == 7:
                xbmc.log("[script.service.hue] Scene not found")
                kodihue.notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(exc)

    def run_stop(self):
        try:
            xbmc.sleep(100)  # sleep for any left over ambilight calls to complete first.
            self.group0.action(scene=self.stopScene)
            xbmc.log("[script.service.hue] In KodiGroup[{}], onPlaybackStop() Stop scene activated")
        except QhueException as exc:
            xbmc.log("[script.service.hue] onPlaybackStopped: Hue call fail: {}: {}".format(exc.type_id, exc.message))
            if exc.type_id == 7:
                xbmc.log("[script.service.hue] Scene not found")
                kodihue.notification(_("Hue Service"), _("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                reporting.process_exception(exc)

    def activate(self):
        xbmc.log("[script.service.hue] Activate group [{}]. State: {}".format(self.kgroupID, self.state))
        xbmc.sleep(200)
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing.
            xbmc.log("[script.service.hue] Activate group [{}]. playback stopped, doing nothing. ".format(self.kgroupID))

    def playback_type(self):
        if self.isPlayingVideo():
            mediaType = VIDEO
        elif self.isPlayingAudio():
            mediaType = AUDIO
        else:
            mediaType = None
        return mediaType

    @staticmethod
    def check_active_time():
        service_enabled = CACHE.get("script.service.hue.service_enabled")
        daylight = CACHE.get("script.service.hue.daylight")
        # xbmc.log("[script.service.hue] Schedule: {}, daylightDisable: {}, daylight: {}, startTime: {}, endTime: {}".format(settings_storage['enableSchedule'], settings_storage['daylightDisable'], daylight, settings_storage['startTime'],
        #         settings_storage['endTime']))

        if settings_storage['daylightDisable'] and daylight:
            xbmc.log("[script.service.hue] Disabled by daylight")
            return False

        if service_enabled:
            if settings_storage['enableSchedule']:
                start = convert_time(settings_storage['startTime'])
                end = convert_time(settings_storage['endTime'])
                now = datetime.datetime.now().time()
                if (now > start) and (now < end):
                    # xbmc.log("[script.service.hue] Enabled by schedule")
                    return True
                # xbmc.log("[script.service.hue] Disabled by schedule")
                return False
            # xbmc.log("[script.service.hue] Schedule not enabled")
            return True

        # xbmc.log("[script.service.hue] Service disabled")
        return False

    def check_video_activation(self, infoTag):
        try:
            duration = infoTag.getDuration() / 60  # returns seconds, convert to minutes
            mediaType = infoTag.getMediaType()
            fileName = infoTag.getFile()
            if not fileName and self.isPlayingVideo():
                fileName = self.getPlayingFile()

            if not fileName and settings_storage['previousFileName']:
                fileName = settings_storage['previousFileName']
            elif fileName:
                settings_storage['previousFileName'] = fileName

            # xbmc.log("[script.service.hue] InfoTag contents: duration: {}, mediaType: {}, file: {}".format(duration, mediaType, fileName))
        except AttributeError:
            xbmc.log("[script.service.hue] Can't read infoTag")
            return False
        # xbmc.log("Video Activation settings({}): minDuration: {}, Movie: {}, Episode: {}, MusicVideo: {}, PVR : {}, Other: {}".format(self.kgroupID, settings_storage['videoMinimumDuration'], settings_storage['video_enableMovie'],
        #                settings_storage['video_enableEpisode'], settings_storage['video_enableMusicVideo'], settings_storage['video_enablePVR'], settings_storage['video_enableOther']))
        # xbmc.log("[script.service.hue] Video Activation ({}): Duration: {}, mediaType: {}, ispvr: {}".format(self.kgroupID, duration, mediaType, fileName[0:3] == "pvr"))
        if ((duration >= settings_storage['videoMinimumDuration'] or fileName[0:3] == "pvr") and
                ((settings_storage['video_enableMovie'] and mediaType == "movie") or
                 (settings_storage['video_enableEpisode'] and mediaType == "episode") or
                 (settings_storage['video_enableMusicVideo'] and mediaType == "MusicVideo") or
                 (settings_storage['video_enablePVR'] and fileName[0:3] == "pvr") or
                 (settings_storage['video_enableOther'] and mediaType != "movie" and mediaType != "episode" and mediaType != "MusicVideo" and fileName[0:3] != "pvr"))):
            xbmc.log("[script.service.hue] Video activation: True")
            return True
        xbmc.log("[script.service.hue] Video activation: False")
        return False

    def check_already_active(self, scene):
        if not scene:
            return False

        xbmc.log("[script.service.hue] Check if scene light already active, settings: enable {}".format(settings_storage['enable_if_already_active']))
        if settings_storage['enable_if_already_active']:
            try:
                sceneData = self.bridge.scenes[scene]()
                for light in sceneData["lights"]:
                    l = self.bridge.lights[light]()
                    if l["state"]["on"]:  # one light is on, the scene can be applied
                        # xbmc.log("[script.service.hue] Check if scene light already active: True")
                        return True
                # xbmc.log("[script.service.hue] Check if scene light already active: False")
            except QhueException as exc:
                xbmc.log("[script.service.hue] checkAlreadyActive: Hue call fail: {}: {}".format(exc.type_id, exc.message))

        return False

    def check_keep_lights_off_rule(self, scene):
        if not scene:
            return True

        xbmc.log("[script.service.hue] Check if lights should stay off, settings: enable {}".format(settings_storage['keep_lights_off']))
        if settings_storage['keep_lights_off']:
            try:
                sceneData = self.bridge.scenes[scene]()
                for light in sceneData["lights"]:
                    l = self.bridge.lights[light]()
                    if l["state"]["on"] is False:  # one light is off, the scene should not be applied
                        xbmc.log("[script.service.hue] Check if lights should stay off: True")
                        return False
                xbmc.log("[script.service.hue] Check if lights should stay off: False")
            except QhueException as exc:
                xbmc.log("[script.service.hue] checkKeepLightsOffRule: Hue call fail: {}: {}".format(exc.type_id, exc.message))

        return True
