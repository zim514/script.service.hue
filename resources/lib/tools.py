from urllib2 import Request, urlopen
import os
import re
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


def get_version():
    # prob not the best way...
    global __xml__
    try:
        for line in open(__xml__):
            if line.find("ambilight") != -1 and line.find("version") != -1:
                return line[line.find("version=")+9:line.find(" provider")-1]
    except:
        return "unknown"


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
    debug_enabled = True

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
