"""Light group management and playback-triggered scene activation.

Defines :class:`LightGroup`, which extends :class:`xbmc.Player` to intercept
playback events (start, pause, stop, resume) and trigger corresponding Hue
scenes. Activation rules are evaluated by :class:`ActivationChecker` which
filters by media type, duration, schedule, daytime, and light state.

Constants:
    STATE_STOPPED (int): Playback is stopped (0).
    STATE_PLAYING (int): Playback is active (1).
    STATE_PAUSED (int): Playback is paused (2).
    VIDEO (int): Video media type identifier (0).
    AUDIO (int): Audio media type identifier (1).
"""
#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.
import inspect
from datetime import datetime

import xbmc
import xbmcgui

from . import ADDON, reporting
from .kodiutils import notification, cache_get, log
from .language import get_string as _

STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2

VIDEO = 0
AUDIO = 1


class LightGroup(xbmc.Player):
    """A light group that triggers Hue scenes in response to Kodi playback events.

    Each instance monitors one media type (video or audio) and activates
    configured play/pause/stop scenes when the corresponding playback event
    fires. Scene activation is gated by :class:`ActivationChecker`.

    Args:
        light_group_id: Numeric group identifier (0=Video, 1=Audio, 3=Ambilight).
        media_type: The media type this group responds to (:data:`VIDEO` or :data:`AUDIO`).
        settings_monitor: Active :class:`~settings.SettingsMonitor` instance.
        bridge: Active :class:`~hue.Hue` instance for API calls.
    """

    def __init__(self, light_group_id, media_type, settings_monitor, bridge=None):
        self.light_group_id = light_group_id
        self.state = STATE_STOPPED
        self.media_type = media_type
        self.info_tag = None
        self.last_media_type = self.media_type
        self.settings_monitor = settings_monitor

        self.activation_check = ActivationChecker(self)
        self.bridge = bridge

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Initialized {self}")

        super().__init__()

    def onAVStarted(self):
        """Called by Kodi when audio/video playback starts.

        Reads the appropriate info tag, validates activation rules, and triggers
        the play scene if all conditions are met. Skips if the group is disabled,
        the bridge is disconnected, or the media type doesn't match.
        """

        self.state = STATE_PLAYING
        self.last_media_type = self._playback_type()
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled")
        play_enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_play_enabled")
        play_scene = getattr(self.settings_monitor, f"group{self.light_group_id}_play_scene")

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackStarted. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}, mediaType: {self.media_type}")

        if not enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] not enabled, doing nothing")
            return
        elif not play_enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] play action not enabled")
            return
        elif not self.bridge.connected:
            log(f"[SCRIPT.SERVICE.HUE] Bridge not connected")
            return
        elif self.media_type != self._playback_type():
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}]: Wrong media type")
            return
        else:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackStarted. play_behavior: {play_enabled}, media_type: {self.media_type} == playback_type: {self._playback_type()}")
            if self.media_type == self._playback_type() and self._playback_type() == VIDEO:
                try:
                    self.info_tag = self.getVideoInfoTag()
                except (AttributeError, TypeError) as exc:
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup{self.light_group_id}: OnAV Started: Can't read VideoInfoTag")
                    reporting.process_exception(exc)
            elif play_enabled and self.media_type == self._playback_type() and self._playback_type() == AUDIO:
                try:
                    self.info_tag = self.getMusicInfoTag()
                except (AttributeError, TypeError) as exc:
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup{self.light_group_id}: OnAV Started: Can't read AudioInfoTag")
                    reporting.process_exception(exc)

            if self.activation_check.validate(play_scene):
                contents = inspect.getmembers(self.info_tag)
                log(f"[SCRIPT.SERVICE.HUE] Start InfoTag: {contents}")

                log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Running Play action")
                self.run_action("play")

    def onPlayBackPaused(self):
        """Called by Kodi when playback is paused.

        Triggers the pause scene if the group is enabled, the bridge is connected,
        and the media type matches.
        """
        self.state = STATE_PAUSED
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled")
        pause_enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_enabled")
        pause_scene = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_scene")

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackPaused. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}")

        if not enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] not enabled, doing nothing")
            return
        elif not pause_enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Pause action not enabled")
            return
        elif not self.bridge.connected:
            log(f"[SCRIPT.SERVICE.HUE] Bridge not connected")
            return
        else:

            if self.media_type == self._playback_type():
                if self.activation_check.validate(pause_scene):
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Running Pause action")
                    self.run_action("pause")

    def onPlayBackStopped(self):
        """Called by Kodi when playback is stopped.

        Triggers the stop scene if the group is enabled, the bridge is connected,
        and the media type matches (using ``last_media_type`` since playback has ended).
        """
        self.state = STATE_STOPPED
        enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_enabled")
        stop_enabled = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_enabled")
        stop_scene = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_scene")

        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] onPlaybackStopped. Group enabled: {enabled}, Bridge connected: {self.bridge.connected}")

        if not enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] not enabled, doing nothing")
            return
        elif not stop_enabled:
            log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Pause action not enabled")
            return
        elif not self.bridge.connected:
            log(f"[SCRIPT.SERVICE.HUE] Bridge not connected")
            return
        else:
            if self.media_type == self.last_media_type or self.media_type == self._playback_type():

                if self.activation_check.validate(stop_scene):
                    log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] Running Stop action")
                    self.run_action("stop")

    def onPlayBackResumed(self):
        """Called by Kodi when playback resumes from pause. Delegates to :meth:`onAVStarted`."""
        self.onAVStarted()

    def onPlayBackError(self):
        """Called by Kodi on playback error. Delegates to :meth:`onPlayBackStopped`."""
        self.onPlayBackStopped()

    def onPlayBackEnded(self):
        """Called by Kodi when playback ends naturally. Delegates to :meth:`onPlayBackStopped`."""
        self.onPlayBackStopped()

    def run_action(self, action):
        """Recall the configured Hue scene for the given playback action.

        Looks up the scene ID and transition time from settings, then calls
        :meth:`~hue.Hue.recall_scene`. If the scene returns 404, clears the
        scene configuration and notifies the user.

        Args:
            action: One of ``"play"``, ``"pause"``, or ``"stop"``.

        Raises:
            RuntimeError: If ``action`` is not a recognized action type.
        """
        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}], run_action({action})")
        service_enabled = cache_get("service_enabled")

        if service_enabled and self.bridge.connected:
            if action == "play":
                scene = getattr(self.settings_monitor, f"group{self.light_group_id}_play_scene")
                duration = getattr(self.settings_monitor, f"group{self.light_group_id}_play_transition")

            elif action == "pause":
                scene = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_scene")
                duration = getattr(self.settings_monitor, f"group{self.light_group_id}_pause_transition")

            elif action == "stop":
                scene = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_scene")
                duration = getattr(self.settings_monitor, f"group{self.light_group_id}_stop_transition")

            else:
                log(f"[SCRIPT.SERVICE.HUE] Unknown action type: {action}")
                raise RuntimeError
            try:
                if self.bridge.recall_scene(scene, duration) == 404:  # scene not found, clear settings and display error message
                    ADDON.setSettingBool(f"group{self.light_group_id}_{action}Behavior", False)
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneName", "Not Selected")
                    ADDON.setSettingString(f"group{self.light_group_id}_{action}SceneID", "-1")
                    log(f"[SCRIPT.SERVICE.HUE] Scene {scene} not found - group{self.light_group_id}_{action}Behavior ")
                    notification(header=_("Hue Service"), message=_("ERROR: Scene not found, it may have been deleted"), icon=xbmcgui.NOTIFICATION_ERROR)


                else:
                    log(f"[SCRIPT.SERVICE.HUE] Scene {scene} recalled")

            except Exception as exc:
                reporting.process_exception(exc)
        log(f"[SCRIPT.SERVICE.HUE] LightGroup[{self.light_group_id}] run_action({action}), service_enabled: {service_enabled}, bridge_connected: {self.bridge.connected}")

    def activate(self):
        """Re-trigger the appropriate action based on current playback state.

        Called at sunset and when the service is re-enabled. Fires the paused
        action if paused, the play action if playing, and does nothing if stopped.
        """
        log(f"[SCRIPT.SERVICE.HUE] Activate group [{self.light_group_id}]. State: {self.state}")
        if self.state == STATE_PAUSED:
            self.onPlayBackPaused()
        elif self.state == STATE_PLAYING:
            self.onAVStarted()
        else:
            # if not playing and activate is called, probably should do nothing. eg. Don't turn lights on when stopped
            log(f"[SCRIPT.SERVICE.HUE] Activate group [{self.light_group_id}]. playback stopped, doing nothing. ")

    def _playback_type(self):
        """Determine the current playback media type.

        Returns:
            :data:`VIDEO` if video is playing, :data:`AUDIO` if audio is playing,
            or ``None`` if nothing is playing.
        """
        if self.isPlayingVideo():
            return VIDEO
        elif self.isPlayingAudio():
            return AUDIO
        else:
            return None



class ActivationChecker:
    """Evaluates whether a Hue scene should be activated based on configured rules.

    Checks include:
        - Video media type and minimum duration filters.
        - Schedule window (start/end time).
        - Daytime disable setting.
        - Light state checks (skip if lights already off, or override schedule if on).

    Args:
        light_group: The parent :class:`LightGroup` instance.
    """

    def __init__(self, light_group: LightGroup):
        self.settings_monitor = light_group.settings_monitor
        self.light_group = light_group
        self.light_group_id = light_group.light_group_id

    def _video_activation_rules(self):
        """Check if the current video meets the configured activation criteria.

        Validates media type (movie, episode, music video, PVR, other) and
        minimum duration settings.

        Returns:
            ``True`` if the video matches the activation rules, ``False`` otherwise.
        """
        minimum_duration = self.settings_monitor.minimum_duration

        movie_setting = self.settings_monitor.movie_setting
        episode_setting = self.settings_monitor.episode_setting
        music_video_setting = self.settings_monitor.music_video_setting
        pvr_setting = self.settings_monitor.pvr_setting
        other_setting = self.settings_monitor.other_setting

        info_tag = self.light_group.info_tag
        duration_minutes = info_tag.getDuration() / 60
        media_type = info_tag.getMediaType()
        file_name = info_tag.getFile()
        if not file_name and self.light_group.isPlayingVideo():
            file_name = self.light_group.getPlayingFile()

        is_pvr = file_name[0:3] == "pvr"

        log(f"[SCRIPT.SERVICE.HUE] _video_activation_rules settings:   minimum_duration: {minimum_duration}, movie_setting: {movie_setting}, episode_setting: {episode_setting}, music_video_setting: {music_video_setting}, pvr_setting: {pvr_setting}, other_setting: {other_setting}")
        log(f"[SCRIPT.SERVICE.HUE] _video_activation_rules values: duration: {duration_minutes}, is_pvr: {is_pvr}, media_type: {media_type}, file_name: {file_name}")

        media_type_matches = ((movie_setting and media_type == "movie") or
                            (episode_setting and media_type == "episode") or
                            (music_video_setting and media_type == "MusicVideo") or
                            (pvr_setting and is_pvr) or
                            (other_setting and media_type not in ["movie", "episode", "MusicVideo"] and not is_pvr))

        if duration_minutes >= minimum_duration and media_type_matches:
            log("[SCRIPT.SERVICE.HUE] _video_activation_rules activation: True")
            return True

        log("[SCRIPT.SERVICE.HUE] _video_activation_rules activation: False")
        return False

    def _is_within_schedule(self):
        """Check if the current time falls within the configured activation schedule.

        Also checks the daytime disable setting — if enabled and it's currently
        daytime (between morning and sunset), returns ``False``.

        Returns:
            ``True`` if activation is allowed by the schedule, ``False`` otherwise.
        """
        if self.settings_monitor.daylight_disable:
            is_daytime = cache_get("daytime")
            if is_daytime:
                log("[SCRIPT.SERVICE.HUE] Disabled by daytime")
                return False

        schedule_enabled = self.settings_monitor.schedule_enabled
        schedule_start = self.settings_monitor.schedule_start
        schedule_end = self.settings_monitor.schedule_end

        if schedule_enabled:
            log(f"[SCRIPT.SERVICE.HUE] Schedule enabled: {schedule_enabled}, start: {schedule_start}, end: {schedule_end}")
            if schedule_start < datetime.now().time() < schedule_end:
                log("[SCRIPT.SERVICE.HUE] _is_within_schedule: True, Enabled by schedule")
                return True
            else:
                log("[SCRIPT.SERVICE.HUE] _is_within_schedule. False, Not within schedule")
                return False

        log("[SCRIPT.SERVICE.HUE] _is_within_schedule: True, Schedule not enabled")
        return True

    def _check_any_lights_on(self, scene_id, all_light_states):
        """Check if any light in the given scene is currently on.

        Args:
            scene_id: The Hue scene resource ID to check.
            all_light_states: Response from the ``GET /light`` API endpoint.

        Returns:
            ``True`` if at least one light in the scene is on, ``False`` otherwise.
        """

        current_scene = next((scene for scene in self.light_group.bridge.scene_data['data'] if scene['id'] == scene_id), None)
        if not current_scene:
            log("[SCRIPT.SERVICE.HUE] _is_scene_already_active: Current scene not found in scene data")
            return False

        for action in current_scene['actions']:
            light_id = action['target']['rid']
            light_state = next((state for state in all_light_states['data'] if state['id'] == light_id), None)
            if light_state and 'on' in light_state and light_state['on']['on']:
                log(f"[SCRIPT.SERVICE.HUE] _is_scene_already_active: Light {light_id} in the scene is on")
                return True

        log("[SCRIPT.SERVICE.HUE] _is_scene_already_active: No lights in the scene are on")
        return False

    def _is_any_light_on(self, scene_id, all_light_states):
        """Check if any light in the given scene is currently on.

        Args:
            scene_id: The Hue scene resource ID to check.
            all_light_states: Response from the ``GET /light`` API endpoint.

        Returns:
            ``True`` if at least one light in the scene is on, ``False`` otherwise.
        """
        current_scene = next((scene for scene in self.light_group.bridge.scene_data['data'] if scene['id'] == scene_id), None)
        if not current_scene:
            log("[SCRIPT.SERVICE.HUE] _is_any_light_on: Current scene not found in scene data")
            return False

        for action in current_scene['actions']:
            light_id = action['target']['rid']
            light_state = next((state for state in all_light_states['data'] if state['id'] == light_id), None)
            if light_state and 'on' in light_state and light_state['on']['on']:
                log(f"[SCRIPT.SERVICE.HUE] _is_any_light_on: Light {light_id} in the scene is on")
                return True
        log(f"[SCRIPT.SERVICE.HUE] _is_any_light_on: All in scene {scene_id} are off")
        return False

    def validate(self, scene=None):
        """Run all activation checks and determine whether to activate the scene.

        Applies rules in priority order:
        1. If ``skip_scene_if_all_off`` and all scene lights are off: reject.
        2. If ``skip_time_check_if_light_on`` and any scene light is on: skip schedule check.
        3. Otherwise, require schedule and (for video) media type/duration rules.

        Args:
            scene: Hue scene ID to validate against, or ``None`` for ambilight
                (which has no scene but still checks schedule/media rules).

        Returns:
            ``True`` if the scene should be activated, ``False`` otherwise.
        """
        skip_time_check_if_light_on = self.settings_monitor.skip_time_check_if_light_on
        skip_scene_if_all_off = self.settings_monitor.skip_scene_if_all_off

        log(f"[SCRIPT.SERVICE.HUE] Validate Activation LightGroup[{self.light_group_id}] Scene: {scene}, media_type: {self.light_group.media_type}, skip_time_check_if_light_on: {skip_time_check_if_light_on}, skip_scene_if_all_off: {skip_scene_if_all_off}")

        all_light_states = None
        if scene and (skip_time_check_if_light_on or skip_scene_if_all_off):
            all_light_states = self.light_group.bridge.make_api_request("GET", "light")

        if self.light_group.media_type == VIDEO and scene:
            # Video with a scene: check light-state overrides, then schedule + media rules
            if skip_scene_if_all_off and not self._is_any_light_on(scene, all_light_states):
                log("[SCRIPT.SERVICE.HUE] Validate video: All lights are off, not activating scene")
                return False
            elif (skip_time_check_if_light_on and self._check_any_lights_on(scene, all_light_states)) and self._video_activation_rules():
                log("[SCRIPT.SERVICE.HUE] Validate video: Some lights are on, skipping schedule check")
                return True
            elif self._is_within_schedule() and self._video_activation_rules():
                log("[SCRIPT.SERVICE.HUE] Validate video: Scene selected, within schedule and video activation rules, activate")
                return True

            log("[SCRIPT.SERVICE.HUE] Validate Video: No valid checks passed, not activating scene")
            return False

        elif self.light_group.media_type == VIDEO:
            # Video without a scene (ambilight): check schedule + media rules only
            if self._is_within_schedule() and self._video_activation_rules():
                log("[SCRIPT.SERVICE.HUE] Validate Video: No scene selected, within schedule and video activation rules: activate")
                return True
            else:
                log("[SCRIPT.SERVICE.HUE] Validate Video: No scene selected, not within schedule or activation rules, ignoring")
                return False

        elif self.light_group.media_type == AUDIO and scene:
            # Audio with a scene: check light-state overrides, then schedule
            if skip_scene_if_all_off and not self._is_any_light_on(scene, all_light_states):
                log("[SCRIPT.SERVICE.HUE] Validate Audio: All lights are off, not activating scene")
                return False
            elif (skip_time_check_if_light_on and self._check_any_lights_on(scene, all_light_states)):
                log("[SCRIPT.SERVICE.HUE] Validate Audio: A light in the scene is on, activating scene")
                return True
            elif self._is_within_schedule():
                log("[SCRIPT.SERVICE.HUE] Validate Audio: Within schedule, activating scene")
                return True
            log("[SCRIPT.SERVICE.HUE] Validate Audio: Checks not passed, not activating")
            return False
