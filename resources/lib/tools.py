from urllib2 import Request, urlopen
import json
import os
import re
import time
import urllib
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__icon__ = os.path.join(__cwd__, "icon.png")
__settings__ = os.path.join(__cwd__, "resources", "settings.xml")
__xml__ = os.path.join(__cwd__, 'addon.xml')

API_KEY = "7OOEGRV8Y2SVNTS29EBJ"
API_SEARCH_URL = "http://www.chapterdb.org/chapters/search"
XML_NAMESPACE = "http://jvance.com/2008/ChapterGrabber"
THRESHOLD_LAST_CHAPTER = 60


def notify(title, msg=''):
    xbmc.executebuiltin('XBMC.Notification({}, {}, 3, {})'.format(
        title, msg, __icon__))

try:
    import requests
except ImportError:
    notify("Kodi Hue", "ERROR: Could not import Python requests")


def get_version():
    # prob not the best way...
    global __xml__
    try:
        for line in open(__xml__):
            if line.find("ambilight") != -1 and line.find("version") != -1:
                return line[line.find("version=")+9:line.find(" provider")-1]
    except:
        return "unknown"


class Light:
    start_setting = None
    group = False
    livingwhite = False
    fullSpectrum = False

    def __init__(self, light_id, settings):
        self.logger = Logger()
        if settings.debug:
            self.logger.debug()

        self.bridge_ip = settings.bridge_ip
        self.bridge_user = settings.bridge_user
        self.mode = settings.mode
        self.light = light_id
        self.dim_time = settings.dim_time
        self.proportional_dim_time = settings.proportional_dim_time
        self.override_hue = settings.override_hue
        self.dimmed_bri = settings.dimmed_bri
        self.dimmed_hue = settings.dimmed_hue
        self.override_sat = settings.override_sat
        self.dimmed_sat = settings.dimmed_sat
        self.undim_sat = settings.undim_sat
        self.override_paused = settings.override_paused
        self.paused_bri = settings.paused_bri
        self.undim_bri = settings.undim_bri
        self.undim_hue = settings.undim_hue
        self.override_undim_bri = settings.override_undim_bri
        self.force_light_on = settings.force_light_on
        self.force_light_group_start_override = settings.force_light_group_start_override

        self.onLast = True
        self.hueLast = 0
        self.satLast = 0
        self.valLast = 0

        self.get_current_setting()
        self.s = requests.Session()

    def request_url_put(self, url, data):
        try:
            response = self.s.put(url, data=data)
            self.logger.debuglog("response: %s" % response)
        except:
            self.logger.debuglog("exception in request_url_put")
            pass  # probably a timeout

    def get_current_setting(self):
        self.logger.debuglog(
            "get_current_setting. requesting from: http://%s/api/%s/lights/%s" %
            (self.bridge_ip, self.bridge_user, self.light))
        r = requests.get("http://%s/api/%s/lights/%s" %
                         (self.bridge_ip, self.bridge_user, self.light))
        j = r.json()

        if isinstance(j, list) and "error" in j[0]:
            # something went wrong.
            err = j[0]["error"]
            if err["type"] == 3:
                notify(
                    "Light Not Found",
                    "Could not find light %s in bridge." %
                    self.light)
            else:
                notify(
                    "Bridge Error",
                    "Error %s while talking to the bridge" %
                    err["type"])
            raise ValueError("Bridge Error", err["type"], err)
            return

        # no error, keep going
        self.start_setting = {}
        state = j['state']
        self.start_setting['on'] = state['on']
        self.start_setting['bri'] = state['bri']
        self.onLast = state['on']
        self.valLast = state['bri']

        lighttype = j['type']
        self.fullSpectrum = (
            (lighttype == 'Color Light') or (
                lighttype == 'Extended Color Light'))

        if 'hue' in state:
            self.start_setting['hue'] = state['hue']
            self.start_setting['sat'] = state['sat']
            self.hueLast = state['hue']
            self.satLast = state['sat']
        else:
            self.livingwhite = True

        self.logger.debuglog(
            "light %s start settings: %s" %
            (self.light, self.start_setting))

    def set_light2(self, hue, sat, bri, duration=None):

        if self.start_setting["on"] == False and self.force_light_on == False:
            # light was not on, and settings say we should not turn it on
            self.logger.debuglog(
                "light %s was off, settings say we should not turn it on" %
                self.light)
            return

        data = {}

        if not self.livingwhite:
            if not hue is None:
                if not hue == self.hueLast:
                    data["hue"] = hue
                    self.hueLast = hue
            if not sat is None:
                if not sat == self.satLast:
                    data["sat"] = sat
                    self.satLast = sat

        self.logger.debuglog(
            "light %s: onLast: %s, valLast: %s" %
            (self.light, self.onLast, self.valLast))
        if bri > 0:
            # don't send on unless we have to (performance)
            if not self.onLast:
                data["on"] = True
                self.onLast = True
            data["bri"] = bri
        else:
            data["on"] = False
            self.onLast = False

        if duration is None:
            if self.proportional_dim_time and self.mode != 0:  # only if its not ambilight mode too
                self.logger.debuglog(
                    "last %r, next %r, start %r, finish %r" %
                    (self.valLast, bri, self.start_setting['bri'], self.dimmed_bri))
                difference = abs(float(bri) - self.valLast)
                total = float(self.start_setting['bri']) - self.dimmed_bri
                proportion = difference / total
                time = int(round(proportion * self.dim_time))
            else:
                time = self.dim_time
        else:
            time = duration

        # moved after time calclation to know the previous value (important)
        self.valLast = bri

        data["transitiontime"] = time

        dataString = json.dumps(data)

        self.logger.debuglog("set_light2: %s: %s" % (self.light, dataString))

        self.request_url_put(
            "http://%s/api/%s/lights/%s/state" %
            (self.bridge_ip, self.bridge_user, self.light),
            data=dataString)

    def flash_light(self):
        self.dim_light()
        time.sleep(self.dim_time/10)
        self.brighter_light()

    def dim_light(self):
        if self.override_hue:
            hue = self.dimmed_hue
        else:
            hue = None

        if self.override_sat:
            sat = self.dimmed_sat
        else:
            sat = None

        self.set_light2(hue, sat, self.dimmed_bri)

    def brighter_light(self):
        if self.override_undim_bri:
            bri = self.undim_bri
        else:
            bri = self.start_setting['bri']

        if not self.livingwhite:
            if self.override_sat:
                sat = self.undim_sat
            else:
                sat = self.start_setting['sat']
            if self.override_hue:
                hue = self.undim_hue
            else:
                hue = self.start_setting['hue']
        else:
            sat = None
            hue = None

        self.set_light2(hue, sat, bri)

    def partial_light(self):
        if self.override_paused:
            bri = self.paused_bri

            if not self.livingwhite:
                if self.override_sat:
                    sat = self.undim_sat
                else:
                    sat = self.start_setting['sat']

                if self.override_hue:
                    hue = self.undim_hue
                else:
                    hue = self.start_setting['hue']
            else:
                sat = None
                hue = None

            self.set_light2(hue, sat, bri)
        else:
            # not enabled for dimming on pause
            self.brighter_light()


class Group(Light):
    group = True
    lights = {}

    def __init__(self, settings, group_id=None):
        if group_id is None:
            self.group_id = settings.group_id
        else:
            self.group_id = group_id

        self.logger = Logger()
        if settings.debug:
            self.logger.debug()

        Light.__init__(self, settings.light1_id, settings)

        for light in self.get_lights():
            tmp = Light(light, settings)
            tmp.get_current_setting()
            self.lights[light] = tmp

    def __len__(self):
        return 0

    def get_lights(self):
        try:
            r = requests.get("http://%s/api/%s/groups/%s" %
                             (self.bridge_ip, self.bridge_user, self.group_id))
            j = r.json()
        except:
            self.logger.debuglog("WARNING: Request fo bridge failed")

        try:
            return j['lights']
        except:
            # user probably selected a non-existing group
            self.logger.debuglog("Exception: no lights in this group")
            return []

    def set_light2(self, hue, sat, bri, duration=None):

        if self.start_setting["on"] == False and self.force_light_on == False:
            # light was not on, and settings say we should not turn it on
            self.logger.debuglog(
                "group %s was off, settings say we should not turn it on" %
                self.group_id)
            return

        data = {}

        if not self.livingwhite:
            if not hue is None:
                if not hue == self.hueLast:
                    data["hue"] = hue
                    self.hueLast = hue
            if not sat is None:
                if not sat == self.satLast:
                    data["sat"] = sat
                    self.satLast = sat

        if bri > 0:
            # don't sent on unless we have to. (performance)
            if not self.onLast:
                data["on"] = True
                self.onLast = True
            data["bri"] = bri
        else:
            data["on"] = False
            self.onLast = False

        if duration is None:
            if self.proportional_dim_time and self.mode != 0:  # only if its not ambilight mode too
                self.logger.debuglog(
                    "last %r, next %r, start %r, finish %r" %
                    (self.valLast, bri, self.start_setting['bri'], self.dimmed_bri))
                difference = abs(float(bri) - self.valLast)
                total = float(self.start_setting['bri']) - self.dimmed_bri
                proportion = difference / total
                time = int(round(proportion * self.dim_time))
            else:
                time = self.dim_time
        else:
            time = duration

        self.valLast = bri  # moved after time calculation

        data["transitiontime"] = time

        dataString = json.dumps(data)

        self.logger.debuglog(
            "set_light2: group_id %s: %s" %
            (self.group_id, dataString))

        self.request_url_put(
            "http://%s/api/%s/groups/%s/action" %
            (self.bridge_ip, self.bridge_user, self.group_id),
            data=dataString)

    def get_current_setting(self):
        r = requests.get("http://%s/api/%s/groups/%s" %
                         (self.bridge_ip, self.bridge_user, self.group_id))
        j = r.json()
        self.logger.debuglog("response: %s" % j)
        if isinstance(j, list) and "error" in j[0]:
            # something went wrong.
            err = j[0]["error"]
            if err["type"] == 3:
                notify(
                    "Group Not Found",
                    "Could not find group %s in bridge." %
                    self.group_id)
            else:
                notify(
                    "Bridge Error",
                    "Error %s while talking to the bridge" %
                    err["type"])
            raise ValueError("Bridge Error", err["type"], err)
            return

        # no error, lets keep going
        self.start_setting = {}
        state = j['action']

        self.start_setting['on'] = state['on']
        if self.force_light_group_start_override:  # override default just in case there is one light on
            for l in self.lights:
                if self.lights[l].start_setting['on']:
                    self.logger.debuglog(
                        "light %s was on, so the group will start as on" % l)
                    self.start_setting['on'] = True
                    break

        self.start_setting['bri'] = state["bri"]
        if self.force_light_group_start_override:
            for l in self.lights:
                if self.start_setting['bri'] < self.lights[
                        l].start_setting['bri']:
                    # take the brightest of the group.
                    self.start_setting['bri'] = self.lights[
                        l].start_setting['bri']

        self.onLast = self.start_setting['on']
        self.valLast = self.start_setting['bri']

        if 'hue' in state:
            self.start_setting['hue'] = state['hue']
            self.start_setting['sat'] = state['sat']
            self.hueLast = state['hue']
            self.satLast = state['sat']
        else:
            self.livingwhite = True

        self.logger.debuglog(
            "group %s start settings: %s" %
            (self.group_id, self.start_setting))

    def request_url_put(self, url, data):
        try:
            response = self.s.put(url, data=data)
            self.logger.debuglog("response: %s" % response)
        except Exception as e:
            # probably a timeout
            self.logger.debuglog("WARNING: Request fo bridge failed")
            pass


class ChapterManager:

    @staticmethod
    def CreditsStartTimeForMovie(title, t_duration=None, chapterCount=None):
        url = "%s?title=%s" % (API_SEARCH_URL, urllib.quote(title))

        if t_duration is not None:
            t_duration = int(round(t_duration))
            xbmc.log(
                "%s: DEBUG %s" %
                ("Kodi Hue",
                 "t_duration %r" %
                 t_duration))
            url += "&duration=%s" % urllib.quote(str(t_duration))

        if chapterCount is not None:
            url += "&chapterCount=%s" % chapterCount

        headers = {"ApiKey": API_KEY}
        request = Request(url, headers=headers)
        response_body = urlopen(request).read()
        root = ET.fromstring(response_body)

        for res_chapterInfo in root.findall("{%s}chapterInfo" % XML_NAMESPACE):
            res_duration = res_chapterInfo.find(
                "{%s}source/{%s}duration" %
                (XML_NAMESPACE, XML_NAMESPACE))
            res_chapters = res_chapterInfo.find("{%s}chapters" % XML_NAMESPACE)
            res_chapterCount = len(res_chapters)

            if t_duration is not None and res_duration is not None:
                t_res_duration = ChapterManager.TotalSecondsForTime(
                    res_duration.text)

                if t_duration != t_res_duration:
                    # durations don't match, skip this result
                    continue

            if chapterCount and chapterCount != res_chapterCount:
                # chapter counts don't match, skip this result
                continue

            res_lastChapter = res_chapters[res_chapterCount - 1]
            t_lastChapterStart = ChapterManager.TotalSecondsForTime(
                res_lastChapter.get("time"))
            # some results include an extra chapter near the end of the movie,
            # so we should use the chapter before it in that case
            if (res_chapterCount > 2 and t_duration is not None and (
                    t_duration - t_lastChapterStart < THRESHOLD_LAST_CHAPTER)):
                res_lastChapter = res_chapters[res_chapterCount - 2]
                t_lastChapterStart = ChapterManager.TotalSecondsForTime(
                    res_lastChapter.get("time"))

            xbmc.log(
                "%s: DEBUG %s" %
                ("Kodi Hue",
                 "selected chapterdb entry with duration %r" %
                 res_duration.text))
            return t_lastChapterStart

        # fall back to trying with no duration specified
        if t_duration is not None:
            return ChapterManager.CreditsStartTimeForMovie(
                title, None, chapterCount)

        return None

    @staticmethod
    def TotalSecondsForTime(time):
        if time:
            m = re.search(
                "(?P<hour>\d{1,2})\:(?P<minute>\d{2})\:(?P<second>\d{2}(?:\.\d+)?)",
                str(time))

            if m is not None:
                t_hours = int(m.group("hour"))
                t_minutes = int(m.group("minute"))
                t_seconds = int(round(float(m.group("second"))))
                return (t_hours * 3600) + (t_minutes * 60) + t_seconds

        return 0

    @staticmethod
    def TotalTimeForSeconds(seconds):
        if seconds is not None:
            total_seconds = int(round(seconds))
            t_hours = total_seconds / 3600
            t_minutes = (total_seconds - t_hours * 3600) / 60
            t_seconds = total_seconds - (t_hours * 3600) - (t_minutes * 60)
            return "%02d:%02d:%02d" % (t_hours, t_minutes, t_seconds)

        return None


class Logger:
    scriptname = "Kodi Hue"
    enabled = True
    debug_enabled = False

    def log(self, msg):
        if self.enabled:
            xbmc.log("%s: %s" % (self.scriptname, msg))

    def debuglog(self, msg):
        if self.debug_enabled:
            self.log("DEBUG %s" % msg)

    def debug(self):
        self.debug_enabled = True

    def disable(self):
        self.enabled = False
