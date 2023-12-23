#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import datetime

import requests
import xbmc
import xbmcgui

from . import ADDON, reporting, ambigroup
from .kodiutils import convert_time, notification, cache_get
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 0
AUDIO = 1


class LightGroup(xbmc.Player):
    def __init__(self, light_group_id, hue_connection, bridge2=None, media_type=VIDEO):
        self.light_group_id = light_group_id
        self.bridge = hue_connection.bridge
        self.hue_connection = hue_connection
        self.state = STATE_STOPPED
        self.media_type = media_type
        self.video_info_tag = xbmc.InfoTagVideo
        self.last_media_type = self.media_type
        self.lights = self.bridge.lights
        self.group0 = self.bridge.groups[0]
        self.bridge2 = bridge2
        self.reload_settings()  # load settings at init

        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] Initialized {self}")
        super().__init__()

    def reload_settings(self):
        self.enabled = ADDON.getSettingBool(f"group{self.light_group_id}_enabled")

        if not isinstance(self, ambigroup.AmbiGroup):
            self.play_behavior = ADDON.getSettingBool(f"group{self.light_group_id}_playBehavior")
            self.play_scene = ADDON.getSettingString(f"group{self.light_group_id}_playSceneID")
            self.play_transition = int(ADDON.getSettingNumber(f"group{self.light_group_id}_playTransition") * 1000)  # Hue API v2 expects milliseconds (int), but we use seconds (float) in the settings because its precise enough and more user-friendly

            self.pause_behavior = ADDON.getSettingBool(f"group{self.light_group_id}_pauseBehavior")
            self.pause_scene = ADDON.getSettingString(f"group{self.light_group_id}_pauseSceneID")
            self.pause_transition = int(ADDON.getSettingNumber(f"group{self.light_group_id}_pauseTransition") * 1000)

            self.stop_behavior = ADDON.getSettingBool(f"group{self.light_group_id}_stopBehavior")
            self.stop_scene = ADDON.getSettingString(f"group{self.light_group_id}_stopSceneID")
            self.stop_transition = int(ADDON.getSettingNumber(f"group{self.light_group_id}_stopTransition") * 1000)

            self.minimum_duration = ADDON.getSettingInt("video_MinimumDuration")
            self.movie_setting = ADDON.getSettingBool("video_Movie")
            self.episode_setting = ADDON.getSettingBool("video_Episode")
            self.music_video_setting = ADDON.getSettingBool("video_MusicVideo")
            self.pvr_setting = ADDON.getSettingBool("video_PVR")
            self.other_setting = ADDON.getSettingBool("video_Other")

    def __repr__(self):
        return f"light_group_id: {self.light_group_id}, enabled: {self.enabled}, state: {self.state}"

    def onAVStarted(self):
        if self.enabled:
            xbmc.log(f"[script.service.hue] In LightGroup[{self.light_group_id}], onPlaybackStarted. Group enabled: {self.enabled},startBehavior: {self.play_behavior} , isPlayingVideo: {self.isPlayingVideo()}, isPlayingAudio: {self.isPlayingAudio()}, self.mediaType: {self.media_type},self.playbackType(): {self.playback_type()}")
            self.state = STATE_PLAYING
            self.last_media_type = self.playback_type()

            if self.isPlayingVideo() and self.media_type == VIDEO:  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                try:
                    self.video_info_tag = self.getVideoInfoTag()
                except RuntimeError as exc:
                    xbmc.log(f"[script.service.hue] Get InfoTag Exception: {exc}")
                    reporting.process_exception(exc)
                    return
                # xbmc.log("[script.service.hue] InfoTag: {}".format(self.videoInfoTag))
                if not self.check_video_activation(self.video_info_tag):
                    return
            else:
                self.video_info_tag = None

            if (self.check_active_time() or self.check_already_active(self.play_scene)) and self.check_keep_lights_off_rule(self.play_scene) and self.play_behavior and self.media_type == self.playback_type():
                xbmc.log(f"[script.service.hue] Run Play")
                self.run_action("play")

    def onPlayBackPaused(self):
        if self.enabled:
            xbmc.log(f"[script.service.hue] In LightGroup[{self.light_group_id}], onPlaybackPaused() , isPlayingVideo: {self.isPlayingVideo()}, isPlayingAudio: {self.isPlayingAudio()}")
            self.state = STATE_PAUSED

            if self.media_type == VIDEO and not self.check_video_activation(self.video_info_tag):  # If video group, check video activation. Otherwise it's audio so we ignore this and continue
                return

            if (self.check_active_time() or self.check_already_active(self.pause_scene)) and self.check_keep_lights_off_rule(self.pause_scene) and self.pause_behavior and self.media_type == self.playback_type():
                self.last_media_type = self.playback_type()
                self.run_action("pause")

    def onPlayBackStopped(self):
        if self.enabled:
            xbmc.log(f"[script.service.hue] In LightGroup[{self.light_group_id}], onPlaybackStopped() , mediaType: {self.media_type}, lastMediaType: {self.last_media_type} ")
            self.state = STATE_STOPPED

            try:
                if self.media_type == VIDEO and not self.check_video_activation(self.video_info_tag):  # If video group, check video activation. Otherwise it's audio so ignore this and check other conditions.
                    return
            except AttributeError:
                xbmc.log("[script.service.hue] No videoInfoTag")

            if (self.check_active_time() or self.check_already_active(self.stop_scene)) and self.check_keep_lights_off_rule(self.stop_scene) and self.stop_behavior and self.media_type == self.last_media_type:
                self.run_action("stop")

    def onPlayBackResumed(self):
        # xbmc.log("[script.service.hue] In LightGroup[{}], onPlaybackResumed()".format(self.light_group_id))
        self.onAVStarted()

    def onPlayBackError(self):
        # xbmc.log("[script.service.hue] In LightGroup[{}], onPlaybackError()".format(self.light_group_id))
        self.onPlayBackStopped()

    def onPlayBackEnded(self):
        # xbmc.log("[script.service.hue] In LightGroup[{}], onPlaybackEnded()".format(self.light_group_id))
        self.onPlayBackStopped()

    def run_action(self, action):
        xbmc.log(f"[script.service.hue] In LightGroup[{self.light_group_id}], run_action({action})")
        service_enabled = cache_get("service_enabled")
        if service_enabled:
            if action == "play":
                scene = self.play_scene
                duration = self.play_transition
            elif action == "pause":
                scene = self.pause_scene
                duration = self.pause_transition
            elif action == "stop":
                scene = self.stop_scene
                duration = self.stop_transition
            else:
                xbmc.log(f"[script.service.hue] Unknown action type: {action}")
                raise RuntimeError
            try:
                if self.bridge2.recall_scene(scene, duration) == 404: #scene not found, clear settings and display error message
                    ADDON.setSettingBool(f"group{self.light_group_id}_{action}Behavior", False)
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneName", "Not Selected")
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneID", "-1")
                    xbmc.log(f"[script.service.hue] Scene {scene} not found - group{self.light_group_id}_{action}Behavior ")
                    notification(header=_("Hue Service"), message=_("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)


                else:
                    xbmc.log(f"[script.service.hue] Scene {scene} recalled")

            except Exception as exc:
                reporting.process_exception(exc)

    def activate(self):
        xbmc.log(f"[script.service.hue] Activate group [{self.light_group_id}]. State: {self.state}")
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing.
            xbmc.log(f"[script.service.hue] Activate group [{self.light_group_id}]. playback stopped, doing nothing. ")

    def playback_type(self):
        if self.isPlayingVideo():
            media_type = VIDEO
        elif self.isPlayingAudio():
            media_type = AUDIO
        else:
            media_type = None
        return media_type

    @staticmethod
    def check_active_time():

        daytime = cache_get("daytime")  # TODO: get daytime from HueAPIv2
        xbmc.log("[script.service.hue] Schedule: {}, daylightDisable: {}, daytime: {}, startTime: {}, endTime: {}".format(ADDON.getSettingBool("enableSchedule"), ADDON.getSettingBool("daylightDisable"), daytime, ADDON.getSettingString("startTime"), ADDON.getSettingString("endTime")))

        if ADDON.getSettingBool("daylightDisable") and daytime:
            xbmc.log("[script.service.hue] Disabled by daytime")
            return False

        if ADDON.getSettingBool("enableSchedule"):
            start = convert_time(ADDON.getSettingString("startTime"))
            end = convert_time(ADDON.getSettingString("endTime"))
            now = datetime.datetime.now().time()
            if (now > start) and (now < end):
                xbmc.log("[script.service.hue] Enabled by schedule")
                return True
            xbmc.log("[script.service.hue] Disabled by schedule")
            return False
        xbmc.log("[script.service.hue] Schedule not enabled")
        return True

    def check_video_activation(self, info_tag):
        try:
            duration = info_tag.getDuration() / 60  # returns seconds, convert to minutes
            media_type = info_tag.getMediaType()
            file_name = info_tag.getFile()
            if not file_name and self.isPlayingVideo():
                file_name = self.getPlayingFile()

            # xbmc.log("[script.service.hue] InfoTag contents: duration: {}, mediaType: {}, file: {}".format(duration, mediaType, fileName))
        except (AttributeError, TypeError):
            xbmc.log("[script.service.hue] Can't read infoTag {exc}")
            return False
        # xbmc.log("Video Activation settings({}): minDuration: {}, Movie: {}, Episode: {}, MusicVideo: {}, PVR : {}, Other: {}".format(self.light_group_id, settings_storage['videoMinimumDuration'], settings_storage['video_enableMovie'],
        #                settings_storage['video_enableEpisode'], settings_storage['video_enableMusicVideo'], settings_storage['video_enablePVR'], settings_storage['video_enableOther']))
        # xbmc.log("[script.service.hue] Video Activation ({}): Duration: {}, mediaType: {}, ispvr: {}".format(self.light_group_id, duration, mediaType, fileName[0:3] == "pvr"))
        if ((duration >= self.minimum_duration or file_name[0:3] == "pvr") and
                ((self.movie_setting and media_type == "movie") or
                 (self.episode_setting and media_type == "episode") or
                 (self.music_video_setting and media_type == "MusicVideo") or
                 (self.pvr_setting and file_name[0:3] == "pvr") or
                 (self.other_setting and media_type != "movie" and media_type != "episode" and media_type != "MusicVideo" and file_name[0:3] != "pvr"))):
            xbmc.log("[script.service.hue] Video activation: True")
            return True
        xbmc.log("[script.service.hue] Video activation: False")
        return False

    def check_already_active(self, scene):
        if not scene:
            return False

        xbmc.log(f"[script.service.hue] Check if scene light already active, settings: enable {ADDON.getSettingBool('enable_if_already_active')}")
        if ADDON.getSettingBool("enable_if_already_active"):
            try:
                scene_data = self.bridge.scenes[scene]()
                for light in scene_data["lights"]:
                    states = self.bridge.lights[light]()
                    if states["state"]["on"]:  # one light is on, the scene can be applied
                        # xbmc.log("[script.service.hue] Check if scene light already active: True")
                        return True
                # xbmc.log("[script.service.hue] Check if scene light already active: False")
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue] Requests exception: {exc}")
                notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
            except Exception as exc:
                reporting.process_exception(exc)
        return False

    def check_keep_lights_off_rule(self, scene):
        if not scene:
            return True

        xbmc.log(f"[script.service.hue] Check if lights should stay off, settings: enable {ADDON.getSettingBool('keep_lights_off')}")
        if ADDON.getSettingBool("keep_lights_off"):
            try:
                scene_data = self.bridge.scenes[scene]()
                for light in scene_data["lights"]:
                    states = self.bridge.lights[light]()
                    if states["state"]["on"] is False:  # one light is off, the scene should not be applied
                        xbmc.log("[script.service.hue] Check if lights should stay off: True")
                        return False
                xbmc.log("[script.service.hue] Check if lights should stay off: False")
            except requests.RequestException as exc:
                xbmc.log(f"[script.service.hue] Requests exception: {exc}")
                notification(header=_("Hue Service"), message=_(f"Connection Error"), icon=xbmcgui.NOTIFICATION_ERROR)
            except Exception as exc:
                reporting.process_exception(exc)

        return True
