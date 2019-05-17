'''
Created on May 12, 2019


'''

import logging

import xbmc
import xbmcaddon
import xbmcgui

import pyxbmct
from qhue import Bridge
from . import kodiHue

from language import get_string as _

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(__name__)


class CreateSceneUI(pyxbmct.AddonDialogWindow):

    def __init__(self,bridge=Bridge):
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        
        self.bridge=bridge
        self.hueLights=bridge.lights
        self.transitionTimeDefault = 10
        
        super(CreateSceneUI, self).__init__(_("Create Hue Scene"))
        
        self.setGeometry(600, 500, 10, 4)
        self.setControls()
        #self.populateLights()
        self.setNavigation()
        # self.set_info_controls()
        # self.set_active_controls()
        # self.set_navigation()
        # Connect a key action (Backspace) to close the window.
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
        

        
        self.doModal()
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        
        
        
        
        

    def setControls(self):
        
        self.textbox = pyxbmct.TextBox()
        self.placeControl(self.textbox, 0, 0, 2, 4)
        self.textbox.setText(_("Create a Hue Scene from current light state") + "\n" + 
                             _("Adjust lights to desired setting in the Hue App to save as a new scene" + "\n" 
                               ))
        
        #####################
        self.placeControl(pyxbmct.Label(_("Scene Name:")), 2, 0,columnspan=2)
        
        self.sceneName = pyxbmct.Edit(_('Scene Name'))
        self.placeControl(self.sceneName, 3, 0,columnspan=2)
        # Additional properties must be changed after (!) displaying a control.
        self.sceneName.setText(_(""))
        
        
        ############ Transition Time
        
        self.transitionTimeLabel = pyxbmct.Label(_("Transition Time: {} secs.").format(self.transitionTimeDefault))
        self.placeControl(self.transitionTimeLabel, 4, 0,columnspan=2)
        
        
        #self.placeControl(self.transitionTimeLabel, 5, 0)
                #

        # Slider
        self.transitionTimeSlider = pyxbmct.Slider()
        self.placeControl(self.transitionTimeSlider, 5, 0,columnspan=2,pad_x=5,pad_y=12)
        self.transitionTimeSlider.setPercent(self.transitionTimeDefault)
        # Connect key and mouse events for slider update feedback.
        self.connectEventList([pyxbmct.ACTION_MOVE_LEFT,
                               pyxbmct.ACTION_MOVE_RIGHT,
                               pyxbmct.ACTION_MOUSE_DRAG,
                               pyxbmct.ACTION_MOUSE_LEFT_CLICK],
                              self.sliderUpdate)
        
        #####

        self.placeControl(pyxbmct.Label(_("Lights to save:")), 2, 2)
        #

        # List
        self.listLights = pyxbmct.List()
        self.placeControl(self.listLights, 3, 2, rowspan=6, columnspan=2)
        # Add items to the list
        
        
        self.listLights.addItems(self.getLights())
        # Connect the list to a function to display which list item is selected.
        
        #self.connect(self.listLights, lambda: xbmc.executebuiltin('Notification(Note!,{0} selected.)'.format(
        #    self.listLights.getListItem(self.listLights.getSelectedPosition()).getLabel())))
        
        
        self.connect(self.listLights, lambda: xbmc.executebuiltin('Notification(Note!,{0} selected.)'.format(
            self.listLights.getListItem(self.listLights.getSelectedPosition()).select(True))))
        
        
        
        # Connect key and mouse events for list navigation feedback.
        self.connectEventList(
            [pyxbmct.ACTION_MOVE_DOWN,
             pyxbmct.ACTION_MOVE_UP,
             pyxbmct.ACTION_MOUSE_WHEEL_DOWN,
             pyxbmct.ACTION_MOUSE_WHEEL_UP,
             pyxbmct.ACTION_MOUSE_MOVE],
            self.listUpdate)

        

        # Bottom Buttons
        
        self.buttonSave = pyxbmct.Button(_('Save'))
        self.placeControl(self.buttonSave, 9, 0)
        
        self.buttonClose = pyxbmct.Button(_('Cancel'))
        self.placeControl(self.buttonClose, 9, 3)
        # Connect control to close the window.
        self.connect(self.buttonClose, self.close)
        
    def setNavigation(self):
        # Set navigation between controls
        self.sceneName.controlDown(self.transitionTimeSlider)
        self.sceneName.controlRight(self.listLights)
        
        self.transitionTimeSlider.controlUp(self.sceneName)
        self.transitionTimeSlider.controlDown(self.buttonSave)
        
        self.buttonSave.controlUp(self.transitionTimeSlider)
        self.buttonSave.controlRight(self.buttonClose)
        
        self.buttonClose.controlLeft(self.buttonSave)
        self.buttonClose.controlUp(self.listLights)
        
        self.listLights.controlLeft(self.sceneName)

        # Set initial focus
        self.setFocus(self.sceneName)            


    def getLights(self):
        

        lights = {}
        listItems=[]
        hueLights = self.hueLights()
        
        for light in hueLights:
            hLight=hueLights[light]
            hLightName=hLight['name']
            
            #logger.debug("In selectHueGroup: {}, {}".format(hgroup,name))
            lights[light] = xbmcgui.ListItem(label=str(hLightName))
            lights[light].select(True)
            listItems.append(xbmcgui.ListItem(label2=light,label=str(hLightName))  )
            #index.append(light)
            #items.append(xbmcgui.ListItem(label=hLightName))
        
        return listItems 
        
        
            
    def sliderUpdate(self):
        # Update slider value label when the slider nib moves
        try:
            if self.getFocus() == self.transitionTimeSlider:
                self.transitionTimeLabel.setLabel(_("Transition Time: {} secs.").format(int(self.transitionTimeSlider.getPercent())))
        except (RuntimeError, SystemError):
            pass

    def listUpdate(self):
        # Update list_item label when navigating through the list.
        try:
            if self.getFocus() == self.list:
                self.list_item_label.setLabel(self.list.getListItem(self.list.getSelectedPosition()).getLabel())
            else:
                self.list_item_label.setLabel('')
        except (RuntimeError, SystemError):
            pass        
                        
        
