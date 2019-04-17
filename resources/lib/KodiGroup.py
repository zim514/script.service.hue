'''
Created on Apr. 17, 2019

@author: Kris
'''
import xbmc
from resources.lib.qhue import qhue

class KodiGroup(xbmc.Player):
    '''
    classdocs
    '''

    def __init__(self, bridge, player, kgroupID):
        '''
        Constructor
        '''
        xbmc.Player.__init__(self)
        
        self.bridge = bridge
        self.player = player
        self.kgroupID=kgroupID
        self.group=bridge.groups[id]
        
        
        
        
    def on_playback_start(self):
        blah=1
        self.group.action(hue=0,sat=255,bri=150,transitiontime=100,on=True)
        