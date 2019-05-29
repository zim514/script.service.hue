#! /usr/bin/python
import os
import sys

from . import globals


######### Based upon: https://raw.githubusercontent.com/Quihico/handy.stuff/master/language.py
######### https://forum.kodi.tv/showthread.php?tid=268081&highlight=generate+.po+python+gettext

_strings = {}

if __name__ == "__main__":

    import polib

    print("PATH: {}".format(sys.path))
    print("executable: " + sys.executable)

    dirpath = os.getcwd()
    print("current directory is : " + dirpath)
    foldername = os.path.basename(dirpath)
    print("Directory name is : " + foldername)

    file = "..\\language\\resource.language.en_GB\\strings.po"

    print("input file: " + file)

    po = polib.pofile(file)

    try:
        import re, subprocess

        command = ["grep", "-hnr", "_([\'\"]", "..\\.."]
        print("grep command: {}".format(command))
        r = subprocess.check_output(command)

        print(r)

        strings = re.compile("_\([\"'](.*?)[\"']\)", re.IGNORECASE).findall(r)
        translated = [m.msgid.lower().replace("'", "\\'") for m in po]
        missing = set([s for s in strings if s.lower() not in translated])
        
        if missing:
            ids_range = list(range(30000, 31000))
            ids_reserved = [int(m.msgctxt[1:]) for m in po]
            ids_available = [x for x in ids_range if x not in ids_reserved]
            print("WARNING: adding missing translation for '%s'" % missing)
            for text in missing:
                id = ids_available.pop(0)
                entry = polib.POEntry(msgid=text, msgstr=u'', msgctxt="#{0}".format(id))
                po.append(entry)
            po.save(file)
    except Exception as e:
        content = []
    with open(__file__, "r") as me:
        content = me.readlines()
        content = content[:content.index("#GENERATED\n") + 1]
    with open(__file__, "w") as f:
        f.writelines(content)
        for m in po:
            line = "_strings['{0}'] = {1}\n".format(m.msgid.lower().replace("'", "\\'"),
                                                    m.msgctxt.replace("#", "").strip())
            f.write(line)
else:
    def get_string(t):
        import xbmc, xbmcaddon
        ADDON = xbmcaddon.Addon()
        ADDON_ID = ADDON.getAddonInfo("id")
        id = _strings.get(t.lower())
        if not id:
            xbmc.log("LANGUAGE: missing translation for '%s'" % t.lower())
            return t
        else:
            if globals.STRDEBUG is True:
                return  "STR:{} {}".format(id,ADDON.getLocalizedString(id))
            else:
                return ADDON.getLocalizedString(id)
        # =======================================================================
        # elif id in range(30000, 31000) and ADDON_ID.startswith("plugin"): return ADDON.getLocalizedString(id)
        # elif id in range(31000, 32000) and ADDON_ID.startswith("skin"): return ADDON.getLocalizedString(id)
        # elif id in range(32000, 33000) and ADDON_ID.startswith("script"): return ADDON.getLocalizedString(id)
        # elif not id in range(30000, 33000): return ADDON.getLocalizedString(id)
        # =======================================================================
    # setattr(__builtin__, "_", get_string)

#GENERATED
_strings['general'] = 1000
_strings['light groups'] = 1100
_strings['player actions'] = 32100
_strings['start/resume video'] = 32201
_strings['pause video'] = 32202
_strings['stop video'] = 32203
_strings['scene name'] = 32510
_strings['scene id'] = 32511
_strings['select scene'] = 32512
_strings['bridge'] = 1200
_strings['discover hue bridge'] = 1210
_strings['bridge ip'] = 1220
_strings['bridge user'] = 1230
_strings['global settings'] = 2100
_strings['advanced'] = 5000
_strings['misc. settings'] = 5100
_strings['initial flash'] = 5110
_strings['flash on settings reload'] = 5111
_strings['group'] = 6000
_strings['kodi group id'] = 6001
_strings['hue group name'] = 6002
_strings['hue group id'] = 6003
_strings['light selection'] = 6100
_strings['select lights'] = 6101
_strings['select hue group'] = 6102
_strings['group behavior'] = 6200
_strings['enabled'] = 6201
_strings['do nothing'] = 6202
_strings['adjust lights'] = 6203
_strings['apply scene'] = 6210
_strings['turn off lights'] = 6204
_strings['initial state'] = 6205
_strings['fade time'] = 6206
_strings['always force on'] = 6207
_strings['hue group'] = 6208
_strings['playback start / resume'] = 6301
_strings['playback pause'] = 6302
_strings['playback stop'] = 6303
_strings['light settings'] = 6400
_strings['initial state'] = 6401
_strings['hue'] = 6402
_strings['saturation'] = 6403
_strings['brightness'] = 6404
_strings['kodi hue'] = 9000
_strings['press connect button on hue bridge'] = 9001
_strings['select hue group...'] = 9002
_strings['create hue group...'] = 9003
_strings['delete hue group...'] = 9004
_strings['force on after sunset'] = 9005
_strings['disable during daytime'] = 9006
_strings['create scene'] = 9007
_strings['delete scene'] = 9008
_strings['select scene'] = 9009
_strings['hue service'] = 30000
_strings['error: group not created'] = 30001
_strings['group deleted'] = 30003
_strings['check your bridge and network'] = 30004
_strings['nupnp discovery... '] = 30005
_strings['hue connected'] = 30006
_strings['press link button on bridge'] = 30007
_strings['bridge not found'] = 30008
_strings['waiting for 90 seconds...'] = 30009
_strings['user not found'] = 30010
_strings['complete!'] = 30011
_strings['group created'] = 30012
_strings['cancelled'] = 30013
_strings['saving settings'] = 30014
_strings['select hue lights...'] = 30015
_strings['are you sure you want to delete this group: '] = 30016
_strings['found bridge: '] = 30017
_strings['discover bridge...'] = 30018
_strings['user found!'] = 30019
_strings['delete hue group'] = 30020
_strings['bridge connection failed'] = 30021
_strings['discovery started'] = 30022
_strings['bridge not configured'] = 30023
_strings['check hue bridge configuration'] = 30024
_strings['error: scene not created'] = 30025
_strings['scene created'] = 30026
_strings['are you sure you want to delete this scene: '] = 30027
_strings['delete hue scene'] = 30028
_strings['create a hue scene from current light state'] = 30029
_strings['enter scene name'] = 30030
_strings['transition time:'] = 30031
_strings['fade time must be saved as part of the scene.'] = 30032
_strings['{} secs.'] = 30033
_strings['cancel'] = 30034
_strings['lights:'] = 30035
_strings['scene name:'] = 30036
_strings['save'] = 30037
_strings['create hue scene'] = 30038
_strings['error: scene not created.'] = 30002
_strings['set a fade time in seconds, or set to 0 seconds for an instant transition.'] = 30039
_strings['scene deleted'] = 30040
_strings['you may now assign your scene to player actions.'] = 30041
_strings['fade time (seconds)'] = 30042
_strings['error'] = 30043
_strings['create new scene'] = 30044
_strings['scene successfully created!'] = 30045
_strings['adjust lights to desired state in the hue app to save as new scene.'] = 30046
