# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

import logging
import xbmc

from resources.lib import globals
from resources.lib.kodiutils import get_setting_as_bool




prefix = b"[{}]".format(globals.ADDONID)
formatter = logging.Formatter(prefix + b'[%(module)s][%(funcName)s](%(lineno)d): %(message)s')
fileFormatter = logging.Formatter(b'%(asctime)s %(levelname)s [%(module)s][%(funcName)s](%(lineno)d): %(message)s')


class KodiLogHandler(logging.StreamHandler):

    def __init__(self):
        logging.StreamHandler.__init__(self)
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

        try:
            xbmc.log(self.format(record), levels[record.levelno])
        except UnicodeEncodeError:
            xbmc.log(self.format(record).encode(
                'utf-8', 'ignore'), levels[record.levelno])

    def flush(self):
        pass


def config():
    separateLogFile=get_setting_as_bool("separateLogFile")
    global logger
    logger = logging.getLogger(globals.ADDONID)

    if separateLogFile:
        if not os.path.isdir(globals.ADDONDIR):
            xbmc.log("Hue Service: profile directory doesn't exist: " + globals.ADDONDIR.encode('utf-8') + "   Trying to create.", level=xbmc.LOGNOTICE)
            try:
                os.mkdir(globals.ADDONDIR)
                xbmc.log("Hue Service: profile directory created: " + globals.ADDONDIR.encode('utf-8'), level=xbmc.LOGNOTICE)
            except OSError as e:
                xbmc.log("Hue Service: Log: can't create directory: " + globals.ADDONDIR.encode('utf-8'), level=xbmc.LOGERROR)
                xbmc.log("Exception: " + str(e.message).encode('utf-8'), xbmc.LOGERROR)

        fileHandler = logging.handlers.TimedRotatingFileHandler(os.path.join(globals.ADDONDIR, 'kodiHue.log'), when="midnight",  backupCount=2)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(fileFormatter)
        logger.addHandler(fileHandler)

    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)


