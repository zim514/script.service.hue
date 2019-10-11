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
- Create and delete multi-room LightScenes
    - Adjust your light's colour and brightness
    - Optional transition time for scenes
    - Supports lights in multiple rooms or groups
    - Edit your scenes in 3rd party apps
    - - Apply selected scene on video or audio player actions
    - Can be disabled based on video type (Episode, Movie or music video) or duration
- Ambilight Support
    - Lighting effects synced with on-screen action
    - Hardware decoding not supported on Android
- Daylight detection
    - Uses Hue's sunrise and sunset settings
    - Disable during daylight hours
    - If sunset falls while watching media, optionally turn on lights
    - Add-on does nothing at sunset if there's no playback
- Enable schedule
    - Set a start and end time at which the add-on should be enabled
    - Time in 24h format (Eg: 22:00, not 10:00 PM)
    - Disable during daylight setting takes precedence over active hours

## Experimental Ambilight Support
You can now configure multiple lights to match playing video as closely as possible.  [Coloured bias lighting](https://en.wikipedia.org/wiki/Bias_lighting)  can reduce eye strain and add colour effects to your media center. 

These settings can impact performance, and may need to be tuned for your set up. 

### Basic Settings:
- **Select Lights:** Only Hue bulbs and lamps that support colours (Gamuts A, B and C) can be used with this system. Lights that can only reproduce whites or color temperatures are ignored.
- **Force on :** Force the selected lights on when playback starts. Otherwise, lights will stay turned off.
- **Minimum & Maximum Brightness:** Sets the brightness
- **Saturation:** Increase the colour saturation factor, with 1 being no change. This can create more colourful effects, but may cause incorrect colours with some content.

### Performance:

Hue has a total limit of 20 commands per second which can be used by all applications and switches. Issuing too many Hue commands can cause your lights to lag or ignore input.
Every selected light increases the number of necessary commands therefore influences how often lights can be updated. For more information on Hue system performance, refer to the [Hue documentation](https://developers.meethue.com/develop/application-design-guidance/hue-system-performance/).
 
- **Update interval:** CPU and Hue impact. The minimum amount of time to wait before updating the lights, in milliseconds. 100ms will update the lights 10 times per second, 500ms, twice per second.
- **Hue transition time:** Hue impact. The amount of time the lights will take to fade from one colour to the next, in milliseconds. Set to 0 for instant transition. 100ms is recommended for a quick and smooth. Hue will wait for this transition to complete before applying the next command. Normally should be the same as the update interval. 
- **Capture size:** CPU impact. Size at which frames are captured, in pixels of X by X. Colour calculation time is too slow with full sized frames, so they are resized first. May affect colour precision as some pixels are lost in the resize process.
- **Average image processing time:** Shows the average time it took to process the colours before updating the Hue bulbs, in milliseconds. This value is updated whenever a video is stopped.


### Problems?

- Make sure you update your Hue bridge to the latest version. This add-on assumes you have the latest features
- Turn on debug logging or the addon's logging (in addon_data)

### Credits:

- [ScreenBloom by Tyler Kershner](https://github.com/kershner/screenBloom) 
- [Qhue by Quentin Stafford-Fraser](https://github.com/quentinsf/qhue)
- [ssdp.py by dankrause](https://gist.github.com/dankrause/6000248)

- [hue-python-rgb-converter (rgbxy) by  Benjamin Knight](https://github.com/benknight/hue-python-rgb-converter)
