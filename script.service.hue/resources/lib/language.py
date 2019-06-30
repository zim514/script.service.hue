#! /usr/bin/python
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
from builtins import range




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
    from .globals import STRDEBUG,ADDON,ADDONID
    from logging import getLogger
    logger = getLogger(ADDONID)
    def get_string(t):

        id = _strings.get(t.lower())
        if not id:
            logger.error("ERROR LANGUAGE: missing translation for '%s'" % t.lower())
            return t
        else:
            if STRDEBUG is True:
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
_strings['video actions'] = 32100
_strings['audio actions'] = 32102
_strings['start/resume'] = 32201
_strings['pause'] = 32202
_strings['stop'] = 32203
_strings['scene name:'] = 32510
_strings['scene id'] = 32511
_strings['select scene...'] = 32512
_strings['bridge'] = 30500
_strings['discover hue bridge'] = 30501
_strings['bridge ip'] = 30502
_strings['bridge user'] = 30503
_strings['bridge serial'] = 30504
_strings['enable schedule (24-h format)'] = 30505
_strings['start time:'] = 30506
_strings['end time:'] = 30507
_strings['disable during daylight'] = 30508
_strings['activate during playback at sunset'] = 30509
_strings['general'] = 30510
_strings['activation schedule'] = 30511
_strings['scenes'] = 30512
_strings['advanced'] = 32101
_strings['debug logs'] = 32102
_strings['separate debug log'] = 32105
_strings['initial flash'] = 5110
_strings['flash on settings reload'] = 5111
_strings['light selection'] = 6100
_strings['select lights'] = 6101
_strings['select hue group'] = 6102
_strings['group behavior'] = 6200
_strings['enabled'] = 6201
_strings['do nothing'] = 6202
_strings['adjust lights'] = 6203
_strings['apply scene'] = 6210
_strings['initial state'] = 6401
_strings['kodi hue'] = 9000
_strings['press connect button on hue bridge'] = 9001
_strings['select hue group...'] = 9002
_strings['create hue group...'] = 9003
_strings['delete hue group...'] = 9004
_strings['create scene'] = 9007
_strings['delete scene'] = 9008
_strings['select scene'] = 9009
_strings['hue service'] = 30000
_strings['error: group not created'] = 30001
_strings['group deleted'] = 30003
_strings['check your bridge and network'] = 30004
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
_strings['connection lost. check settings. shutting down'] = 30047
_strings['connection lost. trying again in 2 minutes'] = 30048
_strings['scene name'] = 30049
_strings['n-upnp discovery...'] = 30050
_strings['upnp discovery...'] = 30051
_strings['searching for bridge...'] = 30005
_strings['invalid start or end time, schedule disabled'] = 30052
