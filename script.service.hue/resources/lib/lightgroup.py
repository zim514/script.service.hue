#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

from datetime import datetime

import xbmc
import xbmcgui

from . import ADDON, reporting
from .kodiutils import convert_time, notification, cache_get
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 0
AUDIO = 1


class LightGroup(xbmc.Player):
    def __init__(self, light_group_id, bridge=None, media_type=VIDEO):
        self.light_group_id = light_group_id
        self.state = STATE_STOPPED
        self.media_type = media_type
        self.video_info_tag = xbmc.InfoTagVideo
        self.last_media_type = self.media_type

        self.activation_check = self.ActivationChecker(self)
        self.bridge = bridge
        self.reload_settings()  # load settings at init

        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] Initialized {self}")
        super().__init__()

    def reload_settings(self):
        # Load LightGroup and AmbiGroup settings
        self.enabled = ADDON.getSettingBool(f"group{self.light_group_id}_enabled")

        if self.enabled and self.bridge.connected:
            self.scene_data = self.bridge.make_api_request("GET", "scene")

        if type(self) is LightGroup:
            #Load LightGroup specific settings
            self.scene_data = self.bridge.make_api_request("GET", "scene")
            self.enable_if_already_active = ADDON.getSettingBool('enable_if_already_active')
            self.keep_lights_off = ADDON.getSettingBool('keep_lights_off')
            self.play_enabled = ADDON.getSettingBool(f"group{self.light_group_id}_playBehavior")
            self.play_scene = ADDON.getSettingString(f"group{self.light_group_id}_playSceneID")
            self.play_transition = int(ADDON.getSettingNumber(f"group{self.light_group_id}_playTransition") * 1000)  # Hue API v2 expects milliseconds (int), but we use seconds (float) in the settings because its precise enough and more user-friendly

            self.pause_enabled = ADDON.getSettingBool(f"group{self.light_group_id}_pauseBehavior")
            self.pause_scene = ADDON.getSettingString(f"group{self.light_group_id}_pauseSceneID")
            self.pause_transition = int(ADDON.getSettingNumber(f"group{self.light_group_id}_pauseTransition") * 1000)

            self.stop_enabled = ADDON.getSettingBool(f"group{self.light_group_id}_stopBehavior")
            self.stop_scene = ADDON.getSettingString(f"group{self.light_group_id}_stopSceneID")
            self.stop_transition = int(ADDON.getSettingNumber(f"group{self.light_group_id}_stopTransition") * 1000)

            self.minimum_duration = ADDON.getSettingInt("video_MinimumDuration")
            self.movie_setting = ADDON.getSettingBool("video_Movie")
            self.episode_setting = ADDON.getSettingBool("video_Episode")
            self.music_video_setting = ADDON.getSettingBool("video_MusicVideo")
            self.pvr_setting = ADDON.getSettingBool("video_PVR")
            self.other_setting = ADDON.getSettingBool("video_Other")

            self.daylight_disable = ADDON.getSettingBool("daylightDisable")

            self.schedule_enabled = ADDON.getSettingBool("enableSchedule")
            self.schedule_start = convert_time(ADDON.getSettingString("startTime"))
            self.schedule_end = convert_time(ADDON.getSettingString("endTime"))

    def __repr__(self):
        return f"light_group_id: {self.light_group_id}, enabled: {self.enabled}, state: {self.state}"

    def onAVStarted(self):
        self.state = STATE_PLAYING
        self.last_media_type = self._playback_type()
        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] onPlaybackStarted. Group enabled: {self.enabled}, Bridge connected: {self.bridge.connected}, mediaType: {self.media_type}")

        if not self.enabled or not self.bridge.connected:
            return
        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] onPlaybackStarted. play_behavior: {self.play_enabled}, media_type: {self.media_type} == playback_type: {self._playback_type()}")
        if self.play_enabled and self.media_type == self._playback_type() and self._playback_type() == VIDEO:

            try:
                self.video_info_tag = self.getVideoInfoTag()
            except (AttributeError, TypeError) as x:
                xbmc.log(f"[script.service.hue] LightGroup{self.light_group_id}: OnAV Started: Can't read infoTag")
                reporting.process_exception(x)
        else:
            self.video_info_tag = None

        if self.activation_check.validate(self.play_scene):
            xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] Running Play action")
            self.run_action("play")

    def onPlayBackPaused(self):
        self.state = STATE_PAUSED
        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] onPlaybackPaused. Group enabled: {self.enabled}, Bridge connected: {self.bridge.connected}")

        if not self.enabled or not self.bridge.connected:
            return

        if self.pause_enabled and self.media_type == self._playback_type():
            if self.activation_check.validate(self.pause_scene):
                xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] Running Pause action")
                self.run_action("pause")

    def onPlayBackStopped(self):
        self.state = STATE_STOPPED
        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] onPlaybackStopped. Group enabled: {self.enabled}, Bridge connected: {self.bridge.connected}")

        if not self.enabled or not self.bridge.connected:
            return

        if self.stop_enabled and (self.media_type == self.last_media_type or self.media_type == self._playback_type()):
            if self.activation_check.validate(self.stop_scene):
                xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] Running Stop action")
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
        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}], run_action({action})")
        service_enabled = cache_get("service_enabled")
        if service_enabled and self.bridge.connected:
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
                if self.bridge.recall_scene(scene, duration) == 404:  # scene not found, clear settings and display error message
                    ADDON.setSettingBool(f"group{self.light_group_id}_{action}Behavior", False)
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneName", "Not Selected")
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneID", "-1")
                    xbmc.log(f"[script.service.hue] Scene {scene} not found - group{self.light_group_id}_{action}Behavior ")
                    notification(header=_("Hue Service"), message=_("ERROR: Scene not found"), icon=xbmcgui.NOTIFICATION_ERROR)


                else:
                    xbmc.log(f"[script.service.hue] Scene {scene} recalled")

            except Exception as exc:
                reporting.process_exception(exc)
        xbmc.log(f"[script.service.hue] LightGroup[{self.light_group_id}] run_action({action}), service_enabled: {service_enabled}, bridge_connected: {self.bridge.connected}")

    def activate(self):
        xbmc.log(f"[script.service.hue] Activate group [{self.light_group_id}]. State: {self.state}")
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing. eg. Don't turn lights on when stopped
            xbmc.log(f"[script.service.hue] Activate group [{self.light_group_id}]. playback stopped, doing nothing. ")

    def _playback_type(self):
        if self.isPlayingVideo():
            media_type = VIDEO
        elif self.isPlayingAudio():
            media_type = AUDIO
        else:
            media_type = None
        return media_type

    class ActivationChecker:
        def __init__(self, parent):
            self.parent = parent

        def _is_within_schedule(self):
            # Fetch daytime status
            daytime = cache_get("daytime")
            # Check if daylight disable setting is on and it's daytime
            if self.parent.daylight_disable and daytime:
                xbmc.log("[script.service.hue] Disabled by daytime")
                return False

            # Check if schedule setting is enabled
            if self.parent.schedule_enabled:
                # Check if current time is within start and end times
                if self.parent.schedule_start < datetime.now().time() < self.parent.schedule_end:
                    xbmc.log("[script.service.hue] Enabled by schedule")
                    return True
                else:
                    xbmc.log("[script.service.hue] Disabled by schedule")
                    return False

            xbmc.log("[script.service.hue] Schedule not enabled, ignoring")
            return True

        def _is_video_activation_valid(self):

            # Fetch video info tag
            info_tag = self.parent.video_info_tag
            # Get duration in minutes
            duration = info_tag.getDuration() / 60
            # Get media type and file name
            media_type = info_tag.getMediaType()
            file_name = info_tag.getFile()
            if not file_name and self.parent.isPlayingVideo():
                file_name = self.parent.getPlayingFile()

            # Check if file is a PVR file
            is_pvr = file_name[0:3] == "pvr"
            # Check if duration is above minimum or if it's a PVR file, and if media type matches settings
            xbmc.log(f"[script.service.hue] _is_video_activation_valid settings:   minimum_duration: {self.parent.minimum_duration}, movie_setting: {self.parent.movie_setting}, episode_setting: {self.parent.episode_setting}, music_video_setting: {self.parent.music_video_setting}, pvr_setting: {self.parent.pvr_setting}, other_setting: {self.parent.other_setting}")
            xbmc.log(f"[script.service.hue] _is_video_activation_valid values: duration: {duration}, is_pvr: {is_pvr}, media_type: {media_type}, file_name: {file_name}")

            if ((duration >= self.parent.minimum_duration or is_pvr) and
                    ((self.parent.movie_setting and media_type == "movie") or
                     (self.parent.episode_setting and media_type == "episode") or
                     (self.parent.music_video_setting and media_type == "MusicVideo") or
                     (self.parent.pvr_setting and is_pvr) or
                     (self.parent.other_setting and media_type not in ["movie", "episode", "MusicVideo"] and not is_pvr))):
                xbmc.log("[script.service.hue] _is_video_activation_valid activation: True")
                return True

            xbmc.log("[script.service.hue] _is_video_activation_valid activation: False")
            return False

        def _is_scene_light_already_active(self, scene_id):
            # Fetch all light states
            all_light_states = self.parent.bridge.make_api_request("GET", "light")

            # Find the current scene from the scene data
            current_scene = next((scene for scene in self.parent.scene_data['data'] if scene['id'] == scene_id), None)
            if not current_scene:
                xbmc.log("[script.service.hue] _is_scene_already_active: Current scene not found in scene data")
                return False

            # Check if any light in the current scene is on
            for action in current_scene['actions']:
                light_id = action['target']['rid']
                light_state = next((state for state in all_light_states['data'] if state['id'] == light_id), None)
                if light_state and 'on' in light_state and light_state['on']['on']:
                    xbmc.log(f"[script.service.hue] _is_scene_already_active: Light {light_id} in the scene is on")
                    return True

            xbmc.log("[script.service.hue] _is_scene_already_active: No lights in the scene are on")
            return False

        def validate(self, scene):
            if self.parent.media_type == VIDEO:
                return (self._is_within_schedule() and
                        self._is_video_activation_valid() and
                        self._is_scene_light_already_active(scene))
            if self.parent.media_type == AUDIO:
                return self._is_within_schedule() and self._is_scene_light_already_active(scene)
