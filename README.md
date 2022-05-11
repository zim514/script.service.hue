[![Addon Checker](https://github.com/zim514/script.service.hue/actions/workflows/check.yml/badge.svg)](https://github.com/zim514/script.service.hue/actions/workflows/check.yml) [![Sync addon metadata translations](https://github.com/zim514/script.service.hue/actions/workflows/sync-addon-metadata-translations.yml/badge.svg)](https://github.com/zim514/script.service.hue/actions/workflows/sync-addon-metadata-translations.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Translation Status](https://kodi.weblate.cloud/widgets/kodi-add-ons-scripts/-/script-service-hue/svg-badge.svg)](https://kodi.weblate.cloud/engage/kodi-add-ons-scripts/)
# **Kodi Service for Philips Hue**
## script.service.hue

Automate your [Hue lights](https://www.meethue.com/) on audio or video playback with [Kodi Media Player](https://kodi.tv/)

## Requirements
- Kodi Matrix 19 or higher
- Hue Bridge V2 (Square)

## Installation

**Stable version**
- [Install from official Kodi repo](https://kodi.wiki/view/Add-on_manager#How_to_install_add-ons_from_a_repository)

**Development version**
 1. [Repo with auto-updates](https://zim514.github.io/repo/repository.snapcase/repository.snapcase-1.0.10.zip) **(Recommended)** or [Download latest .zip version](https://github.com/zim514/script.service.hue/releases/latest)
 2. [Install to Kodi from Zip](https://kodi.wiki/view/HOW-TO:Install_add-ons_from_zip_files)

## Features:
- Create and delete multi-room scenes
    - Adjust your lights' colour and brightness
    - Optional transition time for scenes
    - Supports lights in multiple rooms or zones
    - Edit your scenes in 3rd party apps
    - Apply selected scene on video or audio player actions
    - Can be disabled based on video type or duration
 
- Ambilight Support
    - **_Not supported with all hardware_**
    - Lights synchronize with on-screen colour

- Daylight detection
    - Uses Hue's sunrise and sunset settings
    - Disable during daylight hours
    - If sunset falls while watching media, optionally turn on lights
    - Add-on does nothing at sunset if there's no playback
 
- Scheduling
    - Set a start and end time at which the add-on should be enabled
    - Time in 24h format (Eg: 22:00, not 10:00 PM)
    - Disable during daylight setting takes precedence over active hours

## Experimental Ambilight Support
You can now configure multiple lights to match playing video as closely as possible.  

These settings can impact performance, and may need to be tuned for your set up. 

### Basic Settings:
- **Select Lights:** Only Hue bulbs and lamps that support colour  can be used with this system. Lights that can only reproduce whites or color temperatures are ignored.
- **Force on :** Force the selected lights on when playback starts. Otherwise, lights will stay off.
- **Minimum & Maximum Brightness:** Sets the brightness
- **Saturation:** Increase the colour saturation factor, with 1 being no change. This can create more colourful effects, but less precision.

### Performance:

Hue has a total limit of 20 commands per second which can be used by all applications and switches. Issuing too many Hue commands can cause your lights to lag or ignore input.
Every selected light increases the number of necessary commands therefore influences how often lights can be updated. For more information on Hue system performance, refer to the [Hue documentation](https://developers.meethue.com/develop/application-design-guidance/hue-system-performance/).
 
- **Update interval:** CPU and Hue impact. The minimum amount of time to wait before updating the lights, in milliseconds. 100ms will update the lights 10 times per second, 500ms, twice per second.
- **Hue transition time:** Hue impact. The amount of time the lights will take to fade from one colour to the next, in milliseconds. Set to 0 for instant transition. 100ms is recommended for a quick and smooth. Hue will wait for this transition to complete before applying the next command. Normally should be the same as the update interval. 
- **Capture size:** CPU impact. Size at which frames are captured, in pixels of X by X. Colour calculation time is too slow with full sized frames, so they are resized first. May affect colour precision as some pixels are lost in the resize process.
- **Average image processing time:** Shows the average time it took to process the colours before updating the Hue bulbs, in milliseconds. This value is updated whenever a video is stopped.


## JSON RPC Commands
This addon supports Kodi JSON RPC commands that can be sent by HTTP, other add-ons or skins. These commands simulate the same result as the commands in the plugin menu.

**Disable**:
Temporarily disable service. Service will be re-enabled when Kodi restarts. 
```json
    {
        "jsonrpc": "2.0",
        "method": "JSONRPC.NotifyAll",
        "params": {
            "sender": "script.service.hue",
            "message": "disable"
        },
        "id": 1
    }
```
**Enable**
```json
    {
        "jsonrpc": "2.0",
        "method": "JSONRPC.NotifyAll",
        "params": {
            "sender": "script.service.hue",
            "message": "enable"
        },
        "id": 1
    }
```

**Actions**:

Available commands: play, pause, stop

Video Group: 0

Audio Group: 1

```json
    {
        "jsonrpc": "2.0",
        "method": "JSONRPC.NotifyAll",
        "params": {
            "sender": "script.service.hue",
            "message": "actions",
            "data": {"command": "stop","group": "1"}
        },
        "id": 1
    }
```

## Problems?

- Make sure you update your Hue bridge to the latest version. This add-on assumes you have the latest
- Turn on debug logging

## Includes code from:

- [ScreenBloom by Tyler Kershner](https://github.com/kershner/screenBloom) 
- [Qhue by Quentin Stafford-Fraser](https://github.com/quentinsf/qhue)
- [hue-python-rgb-converter (rgbxy) by  Benjamin Knight](https://github.com/benknight/hue-python-rgb-converter)
