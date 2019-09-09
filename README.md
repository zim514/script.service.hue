[![Build Status](https://travis-ci.com/zim514/script.service.hue.svg?branch=master)](https://travis-ci.com/zim514/script.service.hue) [![CodeFactor](https://www.codefactor.io/repository/github/zim514/script.service.hue/badge)](https://www.codefactor.io/repository/github/zim514/script.service.hue) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
# script.service.hue
**Kodi Service for Philips Hue**
Automate your [Hue lights](https://www.meethue.com/) on audio or video playback with [Kodi Media Player](https://kodi.tv/)

## Requirements
- Kodi Leia 18.x or higher
- Hue Bridge V2 (Square)

## Installation

 1. [Download latest .zip version](https://github.com/zim514/script.service.hue/releases) or [Repo for auto-updates](https://github.com/zim514/zim514.github.io/raw/master/repo/repository.snapcase/repository.snapcase-1.0.0.zip)
 2. [Install to Kodi from Zip](https://kodi.wiki/view/HOW-TO:Install_add-ons_from_zip_files)

## Features:
- Create and delete multi-room Light Scenes
    - Adjust your lights as desired, and use the add-on to select the lights and transition time.
    - Supports lights in multiple rooms or groups.
    - The official Hue app won't show scenes made outside of the official app, but most 3rd party apps will let you see and edit your scene
-   Apply selected scene on playback
    - Select scenes to apply when on Play, Pause and Stop
    - Separate scenes for Audio or Video playback
-   Daylight detection
    - Uses Hue's sunrise and sunset settings
    - Disable during daylight hours
    - If sunset falls while watching media, optionally turn on lights
    - Add-on does nothing at sunset if there's no playback
- Enable schedule
    - Set a start and end time at which the add-on should be enabled
    - Time in 24h format (Eg: 22:00, not 10:00 PM)
    - Disable during daylight setting takes precedence over active hours
    - Not tested if end time is after midnight (Eg. activate from 6PM to 1AM)

## Experimental Ambilight Support
You can now configure multiple lights to match playing video as closely as possible.  [Coloured bias lighting](https://en.wikipedia.org/wiki/Bias_lighting)  can reduce eye strain and add colour effects to your media center. 

This system uses colorgram.py to find the most *predominant* colour in a frame. Colourful/saturated scenes look best, while live action, talk shows or less colorful SD shows tend to generate skin-tones and whites, which still looks good when translated to lighting.

These settings can impact performance, and may need to be tuned for your set up. 

### Basic Settings:
- **Select Lights:** Only Hue bulbs and lamps that support colours (Gamuts A, B and C) can be used with this system. Lights that can only reproduce whites or color temperatures are ignored.
- **Force on & Set Brightness:** Force the selected lights on or to a particular brightness when playback starts. Otherwise, lights will stay at the previous brightness and turned off. This can also be accomplished via Start Scene in Video Actions. Using both can cause conflicts

### Colour Filters:
As the system is based on colour of the current frame, predominantly white and black frames can produce harsh white light. This is mostly noticeable during credit sequences and transitions between scenes or commercials. 
Colour filters allow you to replace full whites or blacks to a selection of neutral white recipes for a more pleasant experience.  
Video rarely has perfect blacks (RGB 0,0,0) or whites (RGB 255,255,255). Colour filters allow you to specify the minimum black or white values to apply to your lights. Outside of that range, the default colour is applied.

 - **RGB Black Filter:** Minimum RGB value to apply colour. Color values below this number are replaced by the Default Colour. Useful 
   to avoid full white on black screens & credits. Setting this too high will replace colours in dark scenes. 
 - **Black replacement colour:** The colour used to replace blacks, from a list of Hue recipies
 - **Colour Sensitivity:** How big the colour change must be for the lights to update. Can reduce flickering by filtering out colours that are too similar to the previous frame. The higher the value, the bigger the colour difference must be for the lights to update. The value represents the distance between two XY points in the CIE1935 colour space used by Hue.
 - **Minimum Colour Proportion:** The percentage of the frame a colour must take to update the lights. Can reduce flickering by filtering out colours that only take up a small portion of the screen. 
 

### Performance:

Hue has a total limit of 20 commands per second which can be used by all applications and switches. Issuing too many Hue commands can cause your lights to lag or ignore input.
Every selected light increases the number of necessary commands therefore influences how often lights can be updated. For more information on Hue system performance, refer to the [Hue documentation](https://developers.meethue.com/develop/application-design-guidance/hue-system-performance/).
- **Number of colours:** CPU impact. The number of colours generated from one frame. With several lights, this will produce a variety of colours. Setting this higher than your number of lights will waste CPU time generating colours that can't be displayed.
- **Update interval:** CPU and Hue impact. The minimum amount of time to wait before updating the lights, in milliseconds. 100ms will update the lights 10 times per second, 500ms, twice per second.
- **Hue transition time:** Hue impact. The amount of time the lights will take to fade from one colour to the next, in milliseconds. Set to 0 for instant transition. 100ms is recommended for a quick and smooth. Hue will wait for this transition to complete before applying the next command. Normally should be the same as the update interval. 
- **Capture size:** CPU impact. Size at which frames are captured, in pixels of X by X. Colour calculation time is too slow with full sized frames, so they are resized first. May affect colour precision as some pixels are lost in the resize process.

Performance logging can be enabled in the advanced setting to check the speed of the colour algorithm and Hue updates. However, these logs are very verbose and should be normally be disabled.


### Problems?

- Make sure you update your Hue bridge to the latest version. This add-on assumes you have the latest features
- Turn on debug logging or the addon's logging (in addon_data)

### Credits:

- Based on original work by @cees-elzinga, @michaelrcarroll, @mpolednik on github
- [Qhue by Quentin Stafford-Fraser](https://github.com/quentinsf/qhue)
- [ssdp.py by dankrause](https://gist.github.com/dankrause/6000248)
- [Colorgram.py by obskyr](https://github.com/obskyr/colorgram.py) 
- [hue-python-rgb-converter (rgbxy) by  Benjamin Knight](https://github.com/benknight/hue-python-rgb-converter)
