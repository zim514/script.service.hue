# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from resources.lib.kodiutils import get_setting_as_bool

import logging
import xbmc
import xbmcaddon
from resources.lib import globals


class KodiLogHandler(logging.StreamHandler):

    def __init__(self):
        logging.StreamHandler.__init__(self)
        #logging.NOTICE ==25 
        logging.Logger.notice=25
        logging.addLevelName(25, "NOTICE")
        #addon_id = xbmcaddon.Addon().getAddonInfo('id')
        prefix = b"[%s] " % globals.ADDONID
        formatter = logging.Formatter(prefix + b'[%(module)s][%(funcName)s](%(lineno)d): %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        levels = {
            logging.CRITICAL: xbmc.LOGFATAL,
            logging.ERROR: xbmc.LOGERROR,
            logging.WARNING: xbmc.LOGWARNING,
#            logging.NOTICE == 25: xbmc.LOGNOTICE,  
            logging.INFO: xbmc.LOGINFO,
            logging.DEBUG: xbmc.LOGDEBUG,
            logging.NOTSET: xbmc.LOGNONE,
        }
        if globals.LOGDEBUG:
            try:
                xbmc.log(self.format(record), levels[record.levelno])
            except UnicodeEncodeError:
                xbmc.log(self.format(record).encode(
                    'utf-8', 'ignore'), levels[record.levelno])

    def flush(self):
        pass


def config():
    logger = logging.getLogger(globals.ADDONID)
    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)
