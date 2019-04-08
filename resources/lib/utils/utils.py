import urllib
import urlparse
import xbmc
from resources.lib.models.constants import PLUGIN_NAME, ACTIONS
from resources.lib.utils.debugger import Debugger


class Utils(object):
    params = None
    query_string = None

    content_type = None
    url = None
    channel_code = None

    def create_qs(self, addon, url_params):
        return addon + '?' + urllib.urlencode(url_params)

    def get_action(self, qs):
        self.query_string = qs
        self.params = urlparse.parse_qs(qs[1:])

        xbmc.log("%s Params %s" % (PLUGIN_NAME, self.params))

        resolved_action = self.params.get("action")
        if resolved_action is not None:
            resolved_action = resolved_action[0]

        self.parse_parameters(resolved_action)
        return resolved_action

    def parse_parameters(self, resolved_action):
        if resolved_action is None:
            self.load_main_screen()
            return

        if resolved_action == ACTIONS['radio_list_item_clicked']:
            self.parse_radio_list_item_clicked()
            return

    def parse_radio_list_item_clicked(self):
        self.url = self.params.get('url')[0]
        self.channel_code = self.params.get('channel_code')[0]

    def load_main_screen(self):
        self.content_type = self.params.get('content_type')[0]

    def construct_known_params(self, addon):
        return self.create_qs(addon, {
            'content_type': self.content_type,
            'url': self.url,
            'channel_code': self.channel_code
        })
