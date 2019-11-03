# -*- coding: utf-8 -*-

from collections import deque

NUM_GROUPS = 2  # group0= video, group1=audio
STRDEBUG = False  # Show string ID in UI
DEBUG = False  # Enable python remote debug
REMOTE_DBG_SUSPEND = False  # Auto suspend thread when debugger attached
QHUE_TIMEOUT = 0.5  # passed to requests, in seconds.

settingsChanged = False
connected = False
daylight = False
forceOnSunset = False
daylightDisable = False
separateLogFile = False
initialFlash = False
reloadFlash = False
enableSchedule = False
performanceLogging = False
ambiEnabled = False
connectionMessage = False

videoMinimumDuration = 0
video_enableMovie  = True
video_enableEpisode = True
video_enableMusicVideo = True
video_enableOther = True

lastMediaType=0

startTime = ""
endTime = ""
processTimes = deque(maxlen=100)
averageProcessTime = 0


