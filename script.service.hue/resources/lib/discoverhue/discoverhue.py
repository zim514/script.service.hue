""" Auto discovery of Hue bridges

Implements UPnP, N-PnP, and IP Scan methods.
TODO: consider allowing a single IP as parameter for validation

Reference:
https://developers.meethue.com/documentation/hue-bridge-discovery

SSDP response will have a location such as
http://192.168.0.???:80/description.xml


Outline:
Enter with optional Serial Numbers and IP's
    Check for bridges at provided IP's
    If not all Serial Numbers have a valid IP, run discovery
    Discovery:
        if running upnp finds nothing,
            if running n-upnp finds nothing,
                if running ip scan finds nothing,
                    return nothing
            else update bridge dict
        else update bridge dict
    If a single serial number was provided
        return the matching address as a string
    otherwise,
        return a dictionary of serial:address pairs
    If the argument was mutable
        remove matched serial numbers from it
"""
import urllib.request
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET
import json
import logging
logger = logging.getLogger('discoverhue')

if __name__ is not '__main__':
    from discoverhue.ssdp import discover as ssdp_discover

class DiscoveryError(Exception):
    """ Raised when a discovery method yields no results """
    pass

def from_url(location):
    """ HTTP request for page at location returned as string

    malformed url returns ValueError
    nonexistant IP returns URLError
    wrong subnet IP return URLError
    reachable IP, no HTTP server returns URLError
    reachable IP, HTTP, wrong page returns HTTPError
    """
    req = urllib.request.Request(location)
    with urllib.request.urlopen(req) as response:
        the_page = response.read().decode()
        return the_page

def parse_description_xml(location):
    """ Extract serial number, base ip, and img url from description.xml

    missing data from XML returns AttributeError
    malformed XML returns ParseError

    Refer to included example for URLBase and serialNumber elements
    """
    class _URLBase(str):
        """ Convenient access to hostname (ip) portion of the URL """
        @property
        def hostname(self):
            return urlsplit(self).hostname

    # """TODO: review error handling on xml"""
    # may want to suppress ParseError in the event that it was caused
    # by a none bridge device although this seems unlikely
    try:
        xml_str = from_url(location)
    except urllib.request.HTTPError as error:
        logger.info("No description for %s: %s", location, error)
        return None, error
    except urllib.request.URLError as error:
        logger.info("No HTTP server for %s: %s", location, error)
        return None, error
    else:
        root = ET.fromstring(xml_str)
        rootname = {'root': root.tag[root.tag.find('{')+1:root.tag.find('}')]}
        baseip = root.find('root:URLBase', rootname).text
        device = root.find('root:device', rootname)
        serial = device.find('root:serialNumber', rootname).text
        # anicon = device.find('root:iconList', rootname).find('root:icon', rootname)
        # imgurl = anicon.find('root:url', rootname).text

        # Alternatively, could look directly in the modelDescription field
        if all(x in xml_str.lower() for x in ['philips', 'hue']):
            return serial, _URLBase(baseip)
        else:
            return None, None

def _build_from(baseip):
    """ Build URL for description.xml from ip """
    from ipaddress import ip_address
    try:
        ip_address(baseip)
    except ValueError:
        # """attempt to construct url but the ip format has changed"""
        # logger.warning("Format of internalipaddress changed: %s", baseip)
        if 'http' not in baseip[0:4].lower():
            baseip = urlunsplit(['http', baseip, '', '', ''])
        spl = urlsplit(baseip)
        if '.xml' not in spl.path:
            sep = '' if spl.path.endswith('/') else '/'
            spl = spl._replace(path=spl.path+sep+'description.xml')
        return spl.geturl()
    else:
        # construct url knowing baseip is a pure ip
        return  urlunsplit(('http', baseip, '/description.xml', '', ''))
    # alternatively:
    # baseip = baseip if baseip[0:4].lower() == 'http' else 'http://'+baseip
    # baseip = baseip if baseip[-4:].lower() == '.xml' else baseip+'/description.xml'
    # return baseip

def parse_portal_json():
    """ Extract id, ip from https://www.meethue.com/api/nupnp

    Note: the ip is only the base and needs xml file appended, and
    the id is not exactly the same as the serial number in the xml
    """
    try:
        json_str = from_url('https://www.meethue.com/api/nupnp')
    except urllib.request.HTTPError as error:
        logger.error("Problem at portal: %s", error)
        raise
    except urllib.request.URLError as error:
        logger.warning("Problem reaching portal: %s", error)
        return []
    else:
        portal_list = []
        json_list = json.loads(json_str)
        for bridge in json_list:
            serial = bridge['id']
            baseip = bridge['internalipaddress']
            # baseip should look like "192.168.0.1"
            xmlurl = _build_from(baseip)
            # xmlurl should look like "http://192.168.0.1/description.xml"
            portal_list.append((serial, xmlurl))
        return portal_list

def via_upnp():
    """ Use SSDP as described by the Philips guide """
    ssdp_list = ssdp_discover("ssdp:all", timeout=5)
    #import pickle
    #with open("ssdp.pickle", "wb") as f:
        #pickle.dump(ssdp_list,f)
    bridges_from_ssdp = [u for u in ssdp_list if 'IpBridge' in u.server]
    logger.info('SSDP returned %d items with %d Hue bridges(s).',
                 len(ssdp_list), len(bridges_from_ssdp))
    # Confirm SSDP gave an accessible bridge device by reading from the returned
    # location.  Should look like: http://192.168.0.1:80/description.xml
    found_bridges = {}
    for bridge in bridges_from_ssdp:
        serial, bridge_info = parse_description_xml(bridge.location)
        if serial:
            found_bridges[serial] = bridge_info

    logger.debug('%s', found_bridges)
    if found_bridges:
        return found_bridges
    else:
        raise DiscoveryError('SSDP returned nothing')

def via_nupnp():
    """ Use method 2 as described by the Philips guide """
    bridges_from_portal = parse_portal_json()
    logger.info('Portal returned %d Hue bridges(s).',
                 len(bridges_from_portal))
    # Confirm Portal gave an accessible bridge device by reading from the returned
    # location.  Should look like: http://192.168.0.1/description.xml
    found_bridges = {}
    for bridge in bridges_from_portal:
        serial, bridge_info = parse_description_xml(bridge[1])
        if serial:
            found_bridges[serial] = bridge_info

    logger.debug('%s', found_bridges)
    if found_bridges:
        return found_bridges
    else:
        raise DiscoveryError('Portal returned nothing')

def via_scan():
    """ IP scan - now implemented """
    import socket
    import ipaddress
    import httpfind
    bridges_from_scan = []
    hosts = socket.gethostbyname_ex(socket.gethostname())[2]
    for host in hosts:
        bridges_from_scan += httpfind.survey(
            # TODO: how do we determine subnet configuration?
            ipaddress.ip_interface(host+'/24').network,
            path='description.xml',
            pattern='(P|p)hilips')
        logger.info('Scan on %s', host)
    logger.info('Scan returned %d Hue bridges(s).', len(bridges_from_scan))
    # Confirm Scan gave an accessible bridge device by reading from the returned
    # location.  Should look like: http://192.168.0.1/description.xml
    found_bridges = {}
    for bridge in bridges_from_scan:
        serial, bridge_info = parse_description_xml(bridge)
        if serial:
            found_bridges[serial] = bridge_info

    logger.debug('%s', found_bridges)
    if found_bridges:
        return found_bridges
    else:
        raise DiscoveryError('Scan returned nothing')

    # TODO: consolidate common code in the 3 via_* routines

def find_bridges(prior_bridges=None):
    """ Confirm or locate IP addresses of Philips Hue bridges.

    `prior_bridges` -- optional list of bridge serial numbers
    * omitted - all discovered bridges returned as dictionary
    * single string - returns IP as string or None
    * dictionary - validate provided ip's before attempting discovery
    * collection or sequence - return dictionary of filtered sn:ip pairs
      * if mutable then found bridges are removed from argument
    """
    found_bridges = {}

    # Validate caller's provided list
    try:
        prior_bridges_list = prior_bridges.items()
    except AttributeError:
        # if caller didnt provide dict then assume single SN or None
        # in either case, the discovery must be executed
        run_discovery = True
    else:
        for prior_sn, prior_ip in prior_bridges_list:
            if prior_ip:
                serial, baseip = parse_description_xml(_build_from(prior_ip))
                if serial:
                    # there is a bridge at provided IP, add to found
                    found_bridges[serial] = baseip
                else:
                    # nothing usable at that ip
                    logger.info('%s not found at %s', prior_sn, prior_ip)
        run_discovery = found_bridges.keys() != prior_bridges.keys()

    # prior_bridges is None, unknown, dict of unfound SNs, or empty dict
    # found_bridges is dict of found SNs from prior, or empty dict
    if run_discovery:
        # do the discovery, not all IPs were confirmed
        try:
            found_bridges.update(via_upnp())
        except DiscoveryError:
            try:
                found_bridges.update(via_nupnp())
            except DiscoveryError:
                try:
                    found_bridges.update(via_scan())
                except DiscoveryError:
                    logger.warning("All discovery methods returned nothing")

    if prior_bridges:
        # prior_bridges is either single SN or dict of unfound SNs
        # first assume single Serial SN string
        try:
            ip_address = found_bridges[prior_bridges]
        except TypeError:
            # user passed an invalid type for key
            # presumably it's a dict meant for alternate mode
            logger.debug('Assuming alternate mode, prior_bridges is type %s.',
                          type(prior_bridges))
        except KeyError:
            # user provided Serial Number was not found
            # TODO: dropping tuples here if return none executed
            # return None
            pass # let it turn the string into a set, eww
        else:
            # user provided Serial Number found
            return ip_address

        # Filter the found list to subset of prior
        prior_bridges_keys = set(prior_bridges)
        keys_to_remove = prior_bridges_keys ^ found_bridges.keys()
        logger.debug('Removing %s from found_bridges', keys_to_remove)
        for key in keys_to_remove:
            found_bridges.pop(key, None)

        # Filter the prior dict to unfound only
        keys_to_remove = prior_bridges_keys & found_bridges.keys()
        logger.debug('Removing %s from prior_bridges', keys_to_remove)
        for key in keys_to_remove:
            try:
                prior_bridges.pop(key, None)
            except TypeError:
                # not a dict, try as set or list
                prior_bridges.remove(key)
            except AttributeError:
                # likely not mutable
                break

        keys_to_report = prior_bridges_keys - found_bridges.keys()
        for serial in keys_to_report:
            logger.warning('Could not locate bridge with Serial ID %s', serial)

    else:
        # prior_bridges is None or empty dict, return all found
        pass

    return found_bridges

if __name__ == '__main__':
    from ssdp import discover as ssdp_discover
    logging.basicConfig(level=logging.INFO,                                                 \
        format='%(asctime)s.%(msecs)03d %(levelname)s:%(module)s:%(funcName)s: %(message)s', \
        datefmt="%Y-%m-%d %H:%M:%S")

    # KNOWN = '0017884e7dad'
    # KNOWN = '0017884e7dad', 'deadbeef'
    # KNOWN = ('0017884e7dad', 'deadbeef')
    # KNOWN = ['0017884e7dad', 'deadbeef']
    # KNOWN = {'0017884e7dad', 'deadbeef'}
    # KNOWN = {'0017884e7dad': None}
    # KNOWN = {'0017884e7dad': 'http://192.168.0.16:80/'}
    # KNOWN = {'0017884e7dad': 'http://192.168.0.27:80/',
    #          'deadbeef7dad': 'http://192.168.0.10:80/'}
    # KNOWN = {'0017884e7dad': 'http://192.168.0.16:80/',
    #          'deadbeef7dad': 'http://192.168.0.10:80/'}
    # KNOWN = None

    logging.info('Start via_upnp')
    print(via_upnp())
    logging.info('Start via_nupnp')
    print(via_nupnp())
    logging.info('Start via_scan')
    print(via_scan())
    logging.info('Stop')
    # print(find_bridges())
