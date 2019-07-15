[![Build Status](https://travis-ci.com/zim514/script.service.hue.svg?branch=master)](https://travis-ci.com/zim514/script.service.hue) [![CodeFactor](https://www.codefactor.io/repository/github/zim514/script.service.hue/badge)](https://www.codefactor.io/repository/github/zim514/script.service.hue) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
# script.service.hue
**Kodi Service for Philips Hue**
Automate your [Hue lights](https://www.meethue.com/) on audio or video playback with [Kodi Media Player](https://kodi.tv/)

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

 - **RGB Black Filter:** Minimum RGB value to apply colour. Color values below this number are replaced by the Default Colour. 
 - **RGB White  Filter:** Maximum RGB value to apply colour. Color values above this number are replaced by the Default Colour. 
 - **Default Colour:** The colour used to replace black or white.
 
 ### Performance:
Performance settings 

## Notes:
- Does not support multiple bridges on your network
- Only tested on LibreElec 9.0.2 & Windows 10, but no reason it shouldn't work anywhere.


## Problems?
- Make sure you update your Hue bridge to the latest version. This add-on assumes you have the latest features
- Turn on debug logging or the addon's logging (in addon_data)


## Credits:
- Based on original work by @cees-elzinga, @michaelrcarroll, @mpolednik on github
- [Qhue by Quentin Stafford-Fraser](https://github.com/quentinsf/qhue)
- [ssdp.py by dankrause](https://gist.github.com/dankrause/6000248)
- [Colorgram.py by obskyr](https://github.com/obskyr/colorgram.py) 
- [hue-python-rgb-converter (rgbxy) by  Benjamin Knight](https://github.com/benknight/hue-python-rgb-converter)
<!--stackedit_data:
eyJoaXN0b3J5IjpbLTk4ODk5NDM3MCw1MzcwODk0MjAsNzExMj
kxOTI2XX0=
-->