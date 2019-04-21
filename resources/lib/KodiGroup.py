'''
Created on Apr. 17, 2019

@author: Kris
'''
import xbmc
from resources.lib.qhue import qhue

class KodiGroup(xbmc.Player):
        def __init__(self):
            super(xbmc.Player,self).__init__()

        def readSettings(self):
            a=1
            
        def setup(self,bridge,kgroupID,hgroupID):
            self.readSettings()
            self.bridge = bridge
            self.kgroupID=kgroupID
            self.hgroupID=hgroupID
#            bridge.groups()
            self.group=bridge.groups[hgroupID]()
            
        
        def onPlayBackStarted(self):
            #blah=1
            self.group.action(hue=0,sat=255,bri=250,transitiontime=50,on=True)
            
        def onPlayBackStopped(self):
            #blah=1
            self.group.action(hue=0,sat=255,bri=250,transitiontime=50,on=True)
        
        def onPlayBackPaused(self):
            #blah=1
            self.group.action(hue=0,sat=255,bri=250,transitiontime=50,on=True)
                
        def onPlayBackResumed(self):
            self.onPlayStarted()            
                
        def onPlayBackError(self):
            self.onPlayBackStopped()            
                
        def onPlayBackEnded(self):
            self.onPlayBackStopped()
            

        

