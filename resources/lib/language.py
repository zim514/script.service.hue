#! /usr/bin/python
import sys
import os




######### https://raw.githubusercontent.com/Quihico/handy.stuff/master/language.py
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
            ids_range = range(30000, 31000)
            ids_reserved = [int(m.msgctxt[1:]) for m in po]
            ids_available = [x for x in ids_range if x not in ids_reserved]
            print("WARNING: missing translation for '%s'" % missing)
            for text in missing:
                id = ids_available.pop(0)
                entry = polib.POEntry(msgid=text, msgstr=u'', msgctxt="#{0}".format(id))
                po.append(entry)
            po.save(file)
    except Exception as e:
        print(e)
    content = []
    with open(__file__, "r") as me:
        content = me.readlines()
        content = content[:content.index("#GENERATED\n")+1]
    with open(__file__, "w") as f:
        f.writelines(content)
        for m in po:
            line = "_strings['{0}'] = {1}\n".format(m.msgid.lower().replace("'", "\\'"), m.msgctxt.replace("#", "").strip())
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
            return ADDON.getLocalizedString(id)
        #=======================================================================
        # elif id in range(30000, 31000) and ADDON_ID.startswith("plugin"): return ADDON.getLocalizedString(id)
        # elif id in range(31000, 32000) and ADDON_ID.startswith("skin"): return ADDON.getLocalizedString(id)
        # elif id in range(32000, 33000) and ADDON_ID.startswith("script"): return ADDON.getLocalizedString(id)
        # elif not id in range(30000, 33000): return ADDON.getLocalizedString(id)
        #=======================================================================
    #setattr(__builtin__, "_", get_string)


#GENERATED
_strings['general'] = 1000
_strings['group 1'] = 1001
_strings['group 2'] = 1002
_strings['group 3'] = 1003
_strings['group 4'] = 1004
_strings['light groups'] = 1100
_strings['setup theater lights'] = 1120
_strings['setup ambilight lights'] = 1130
_strings['setup static lights'] = 1140
_strings['bridge'] = 1200
_strings['discover hue bridge'] = 1210
_strings['bridge ip'] = 1220
_strings['bridge user'] = 1230
_strings['warning: reset all settings'] = 1400
_strings['reset all settings (requires disable/re-enable)'] = 1410
_strings['debug mode'] = 1420
_strings['theater'] = 2000
_strings['global settings'] = 2100
_strings['setup theater subgroup'] = 2105
_strings['dim time'] = 2110
_strings['proportional dim time'] = 2120
_strings['example: take 70% of transition time if dimming 70%'] = 2130
_strings['playback start (or resume)'] = 2200
_strings['override brightness (default 30)'] = 2210
_strings['choose brightness'] = 2220
_strings['playback pause'] = 2300
_strings['only undim subgroup'] = 2305
_strings['override brightness (default initial)'] = 2310
_strings['choose brightness'] = 2320
_strings['playback stop'] = 2400
_strings['override brightness (default initial)'] = 2410
_strings['choose brightness'] = 2420
_strings['ambilight'] = 3000
_strings['global settings'] = 3100
_strings['minimum brightness'] = 3110
_strings['maximum brightness'] = 3120
_strings['enable dimming'] = 3130
_strings['thresholds'] = 3200
_strings['value'] = 3210
_strings['saturation'] = 3220
_strings['color'] = 3300
_strings['bias'] = 3310
_strings['sensitivity: 6=variety with >1 light, 36=accuracy'] = 3320
_strings['playback start (or resume)'] = 3400
_strings['override brightness (default 30)'] = 3420
_strings['choose brightness'] = 3430
_strings['playback pause'] = 3500
_strings['override brightness (default initial)'] = 3510
_strings['choose brightness'] = 3520
_strings['playback stop'] = 3600
_strings['override brightness (default initial)'] = 3610
_strings['choose brightness'] = 3620
_strings['static'] = 4000
_strings['playback start (or resume)'] = 4100
_strings['random color'] = 4105
_strings['override hue (default initial)'] = 4110
_strings['choose hue'] = 4120
_strings['override saturation (default initial)'] = 4130
_strings['choose saturation'] = 4140
_strings['override brightness (default 100)'] = 4150
_strings['choose brightness'] = 4160
_strings['advanced'] = 5000
_strings['misc. settings'] = 5100
_strings['initial flash'] = 5110
_strings['flash on settings reload'] = 5111
_strings['disable for short movies'] = 5120
_strings['short movie threshold (seconds)'] = 5130
_strings['force light(s) on (even if off)'] = 5140
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
_strings['turn off lights'] = 6204
_strings['initial state'] = 6205
_strings['fade time'] = 6206
_strings['force on'] = 6207
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
_strings['force on at sunset'] = 9005
_strings['disable during daytime'] = 9006
_strings['hue service'] = 30000
_strings['error: group not created'] = 30001
_strings['localized notification'] = 30002
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
