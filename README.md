script.kodi.hue.ambilight
=========================

A Kodi add-on that controls Philips Hue lights. In "Theater mode" the add-on dims the the Philips Hue lights as soon as a movie starts playing, and turns the lights back on once the movie is done. "Ambilight mode" turns your Philips Hue lights in a room-sized ambilight.

Support
-------
This is a side project for me, and as such I'll update it when and if I have time . I'll happily respond to issues and feature requests (provided that they are detailed enough to realistically debug your problem (**LOGS**)). Since this is based on @cees-elzinga's original work, I've only modified some of the functions to enhance the features. I don't personally use the ambilight feature, and therefore havent done much testing with it... Again, happy to try and help out, but don't expect super-quick responses!

Please fork and enhance! Pull requests welcome!

Debugging
---------
Please turn on Debug Logging through the addon (Configure -> Advanced Settings -> Debug Logging) and follow the procedure at http://kodi.wiki/view/Log_file/Easy to upload a log file. Provide a link to your logfile in the issue.

Installation
------------

The add-on depends on the Kodi add-on "requests" for the ambilight mode.

**Kodi add-on script.module.requests**

 - Download the add-on as a ZIP file from https://github.com/beenje/script.module.requests
  - (Right click on the "ZIP" icon and select "Download Linked File").
 - Open Kodi
 - Go to `System -> Settings -> Add-ons -> Install from zip file`
 - Select the zip file.

**Kodi add-on script.kodi.hue.ambilight**

 - Download the add-on as a ZIP file from the top of this page
   - (Right click on the "ZIP" icon and select "Download Linked File")
 - Open Kodi
 - Go to `System -> Settings -> Add-ons -> Install from zip file`
 -  Restart Kodi and configure the add-on:
   - `System -> Settings -> Add-ons -> Enabled add-ons -> Services -> Kodi Philips Hue`
   - Run `Start auto discovery of bridge IP and User`.

Note for Raspberry Pi users:

 - Save the add-on configuration by exiting Kodi before shutting down the Pi completely
 - Ambilight mode doesn't work on a Raspberry Pi due to the way it renders video

Release history
---------------
  * 2015-07-27 v 0.8.0 Added credit detection (through chapterdb.com), proportional transition times based on brightness
  * 2015-11-02 v 0.7.2 Minor update, attempting to resolve autodiscover issues
  * 2015-07-26 v 0.7.1 Updated Icon, code refactor, bugfixes, better group performance, handling of "pause during screen refresh rate change" setting
  * 2015-01-15 v 0.7.0 Fixed Kodi references, added paused brightness override (changes beginning here by @michaelrcarroll)
  * 2014-01-12 v 0.6.2 Minor improvements
  * 2013-07-13 v 0.6.0 General improvements all around (by robwalch)
  * 2013-05-25 v 0.5.0 Debug logging, livingwhite lights
  * 2013-05-04 v 0.4.0 Advanced settings
  * 2013-04-25 v 0.3.6 Custom dimmed brightness in theatre mode
  * 2013-04-02 v 0.3.4 Ambilight is more responsive
  * 2013-04-01 v 0.3.3 Rename to script.xbmc.hue.ambilight
  * 2013-02-25 v 0.3.1 Improved handling for grouped lights
  * 2013-01-27 v 0.1.0 Initial release

TODO:
-----
  * Add: saturation override so that full light parameters can be overridden
  * Fix: lights may turn on if they are already off, need better state checking
  * Add: setting to customize what is considered a "short" video
  * Add: *experimental* auto undim when movie reaches credits (does not always work, may ruin your movie-watching experience)
  * Refactor: clean up a lot of the old code that's still in the addon, but not necessary
  * Add: [OpenHAB](http://github.com/openhab/openhab) support for a grouped switch endpoint (to turn off a set of lights that are controlled by something other than Philips Hue... i.e. Z-Wave)
  * Publish: get addon onto the official Kodi addon repository
