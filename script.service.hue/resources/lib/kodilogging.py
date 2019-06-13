# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
from globals import ADDONID
import xbmc

class KodiLogHandler(logging.StreamHandler):

    def __init__(self):
        logging.StreamHandler.__init__(self)
        
        prefix = b"[%s] " % ADDONID
        formatter = logging.Formatter(prefix + b'%(name) $(funcName)s: %(message)s\n')
        self.setFormatter(formatter)
        
        
        

    def emit(self, record):
        levels = {
            logging.CRITICAL: xbmc.LOGFATAL,
            logging.ERROR: xbmc.LOGERROR,
            logging.WARNING: xbmc.LOGWARNING,
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
    logger = logging.getLogger()
    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)
    return logger
    
