#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import xbmc
import json

def get_log_mediainfo():
    """
    Retrieves dimensions and framerate information from XBMC.log or kodi.log
    Will likely fail if XBMC in debug mode - could be remedied by increasing the number of lines read
    Props: http://stackoverflow.com/questions/260273/most-efficient-way-to-search-the-last-x-lines-of-a-file-in-python
    @return: dict() object with the following keys:
                                'pwidth' (int)
                                'pheight' (int)
                                'par' (float)
                                'dwidth' (int)
                                'dheight' (int)
                                'dar' (float)
                                'fps' (float)
    @rtype: dict()
    """
    exec_version = float(str(xbmc.getInfoLabel("System.BuildVersion"))[0:4])
    if exec_version < 14.0:
        logfn = xbmc.translatePath(r'special://logpath/xbmc.log')
    else:
        logfn = xbmc.translatePath(r'special://logpath/kodi.log')
    if is_xbmc_debug():
        lookbacksize = 6144
        lookbacklines = 60
    else:
        lookbacksize = 2560
        lookbacklines = 25
    ret = None
    numretries = 4
    while numretries > 0:
        xbmc.sleep(250)
        try:
            with open(logfn, "r") as f:
                f.seek(0, 2)           # Seek @ EOF
                fsize = f.tell()        # Get Size
                f.seek(max(fsize - lookbacksize, 0), 0)  # Set pos @ last n chars
                lines = f.readlines()       # Read to end
            lines = lines[-lookbacklines:]    # Get last n lines

            for line in lines:
                if 'fps:' in line:
                    start = line.find('fps:')
                    sub = line[start:].rstrip('\n')
                    tret = dict(item.split(":") for item in sub.split(","))
                    ret = {}
                    for key in tret:
                        tmp = key.strip()
                        try:
                            if tmp == 'fps':
                                ret['fps'] = float(tret[key])
                            else:
                                ret[tmp] = int(tret[key])
                        except ValueError:
                            pass
                    if ret['pheight'] != 0:
                        ret['par'] = float(ret['pwidth'])/float(ret['pheight'])
                    if ret['dheight'] != 0:
                        ret['dar'] = float(ret['dwidth'])/float(ret['dheight'])
        except Exception as e:
            xbmc.log('Error opening logfile: {0}'.format(logfn))
            if hasattr(e, 'message'):
                xbmc.log('Error message: {0}'.format(e.message))
            numretries = 0
        if ret is not None:
            numretries = 0
    if ret is None:
        xbmc.log('Could not retrieve video info from log')
    return ret


def is_xbmc_debug():
    json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Settings.getSettings", "params":'
                                     ' { "filter":{"section":"system", "category":"debug"} } }')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = json.loads(json_query)

    if json_response.has_key('result') and json_response['result'].has_key('settings') and json_response['result']['settings'] is not None:
        for item in json_response['result']['settings']:
            if item["id"] == "debug.showloginfo":
                if item["value"] is True:
                    return True
                else:
                    return False