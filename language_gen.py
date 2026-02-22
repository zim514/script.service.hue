#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

# Based upon: https://raw.githubusercontent.com/Quihico/handy.stuff/master/language.py
# https://forum.kodi.tv/showthread.php?tid=268081&highlight=generate+.po+python+gettext


import os
import re
import subprocess
import polib

_strings = {}

# print(f"PATH: {sys.path}")
# print(f"executable: {sys.executable}")

dir_path = os.getcwd()
folder_name = os.path.basename(dir_path)

print(f"current directory is : {dir_path}")
print(f"Directory name is : {folder_name}")

string_file = f"{dir_path}/script.service.hue/resources/language/resource.language.en_gb/strings.po"
code_file = f"{dir_path}/script.service.hue/resources/lib/language.py"
code_base = os.path.join(dir_path, "script.service.hue", "resources", "lib")

print(f"input file: {string_file}")
print(f"code file: {code_file}")
print(f"__file__: {__file__}")
print(f"grep location: {code_base}")

po = polib.pofile(string_file, wrapwidth=500)

try:
    command = ["grep", "-hnr", "_([\'\"]", code_base]
    print(f"grep command: {command}")
    r = subprocess.check_output(command, text=True)

    print(r)
    print("End grep")

    # Read the language.py file
    with open(f"{dir_path}/script.service.hue/resources/lib/language.py", "r") as f:
        lang_file_text = f.read()

    # Parse existing IDs
    existing_mapping = dict(re.findall(r"_strings\['(.*?)'\] = (\d+)", lang_file_text))

    strings = re.compile(r"_\(f?[\"'](.*?)[\"']\)", re.IGNORECASE).findall(r)
    translated = [m.msgid.lower().replace("'", "\\'") for m in po]
    mapped = {s.lower(): existing_mapping.get(s.lower()) for s in strings}
    missing = set([s for s, i in mapped.items() if s.lower() not in translated and i is None])

    # strings = re.compile('_\(f?["\'](.*?)["\']\)', re.IGNORECASE).findall(r)
    # translated = [m.msgid.lower().replace("'", "\\'") for m in po]
    # missing = set([s for s in strings if s.lower() not in translated])

    ids_range = list(range(30000, 35000))
    # ids_reserved = [int(m.msgctxt[1:]) for m in po]
    ids_reserved = []
    for m in po:
        # print(f"msgctxt: {m.msgctxt}")
        if str(m.msgctxt).startswith("#"):
            ids_reserved.append(int(m.msgctxt[1:]))

    ids_available = [x for x in ids_range if x not in ids_reserved]
    # print(f"IDs Reserved: {ids_reserved}")
    print(f"Available IDs: {ids_available}")
    print(f"Missing: {missing}")

    if missing:
        print(f"WARNING: adding missing translation for '{missing}'")
        for text in missing:
            string_id = ids_available.pop(0)
            entry = polib.POEntry(msgid=text, msgstr='', msgctxt=f"#{string_id}")
            po.append(entry)
        po.save(string_file)
except Exception as e:
    print(f"Exception: {e}")
    content = []

with open(code_file, "r") as me:
    content = me.readlines()
    try:
        generated_index = next(i for i, s in enumerate(content) if '# GENERATED' in s)
        content = content[:generated_index + 1]
    except StopIteration:
        print("'# GENERATED' was not found in content")

with open(code_file, "w", newline="\n") as f:
    f.writelines(content)
    for m in po:
        if m.msgctxt.startswith("#"):
            # If the string is already mapped, use existing mapping else create new.
            string_id = mapped.get(m.msgid.lower(), m.msgctxt.replace("#", "").strip())
            line = '_strings[\'%s\'] = %s\n' % (m.msgid.lower().replace("'", "\\'"), string_id)
            f.write(line)
