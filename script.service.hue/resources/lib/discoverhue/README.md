# **discoverhue**

[![The MIT License](https://img.shields.io/badge/license-MIT-orange.svg?style=flat-square)](http://opensource.org/licenses/MIT)

> Discovery of hue bridges per the Philips design guide.

Use *discoverhue* to find the IP addresses of all hue bridges on the LAN. If
previously known bridge serial numbers are provided then the returned info will
be filtered.  Alternatively, serial numbers and last known IP addresses pairs
may be provided.  In this case, the provided addresses will be checked first
and the discovery methods will only be executed if unmatched bridges remain.

Currently, *discoverhue* implements options one,two, and three of the Hue Bridge
Discovery Guide available with registration at
[MeetHue](https://developers.meethue.com/application-design-guidance).

## Installation

```shell
pip install discoverhue
```

## Examples

Execute discovery and return a dictionary of all found bridges:

```python
import discoverhue
found = discoverhue.find_bridges()
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge]))
```

Execute discovery and return a filtered list of bridges:

```python
# using a list, matches will be removed from search_id
search_id = ['0017884e7dad', '001788102201']
found = discoverhue.find_bridges(search_id)

# using a set, matches will be removed from search_id
search_id = {'0017884e7dad', '001788102201'}
found = discoverhue.find_bridges(search_id)

# using a tuple, immutable so matches will not be removed
search_id = ('0017884e7dad', '001788102201')
found = discoverhue.find_bridges(search_id)
```

Execute discovery and return single IP address as string:

```python
>>> found = discoverhue.find_bridges('001788102201')
>>> found.lower()
'http://192.168.0.1:80/'
```

Validate provided IP's and execute discovery only if necessary:

```python
>>> discoverhue.find_bridges({'0017884e7dad':'192.168.0.1',
                              '001788102201':'192.168.0.2'})
{'0017884e7dad': 'http://192.168.0.27:80/'}
```

## Contributions

Welcome at https://github.com/Overboard/discoverhue

## Status

Released.

### SSDP Attribution

* Original compliments of @dankrause at
  * https://gist.github.com/dankrause/6000248
* Python3 support from @voltagex at
  * https://github.com/voltagex/junkcode/blob/master/Python/dlna_downloader/ssdp.py
* Server field addition and Win32 @Overboard at
  * https://github.com/Overboard/discoverhue/blob/master/discoverhue/ssdp.py
