'''
Created on May 12, 2019


'''

import os
import xbmc
import logging
import xbmcaddon

import pyxbmct

import globals



ADDON = xbmcaddon.Addon()
logger = logging.getLogger(__name__)


class createSceneUI(pyxbmct.AddonDialogWindow):
    '''
    classdocs
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
        