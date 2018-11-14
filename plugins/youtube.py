import urllib.parse
import requests

from datetime import timedelta
from plugin import *


class youtube(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.yt_api_url = 'https://www.googleapis.com/youtube/v3/search' \
                          '?part=snippet' \
                          '&order=%s' \
                          '&type=video' \
                          '&key=%s' \
                          '&q=%s'

        self.yt_url = 'https://www.youtube.com/watch?v=%s'

    @command
    @doc('yt <ask>: search youtube for <ask>')
    def yt(self, msg, sender_nick, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked youtube about {msg}')
        response = self.get_yt_data(msg)
        if not response:
            self.bot.say('youtube api error')
            return

        if len(response['items']) == 0:
            self.bot.say_err()
            return

        result_count = min(self.config['results'], len(response['items']))
        for item in [response['items'][it] for it in range(0, result_count)]:
            prefix = color.cyan(f'[{item["snippet"]["title"]}]')
            self.bot.say(f'{prefix} {self.yt_url % item["id"]["videoId"]}')

    @utils.timed_lru_cache(expiration=timedelta(minutes=3), typed=True)
    def get_yt_data(self, ask):
        ask = urllib.parse.quote(ask)
        response = requests.get(self.yt_api_url % (self.config['order_by'], self.config['api_key'], ask)).json()
        if 'error' not in response and 'items' in response: return response
        else:
            self.logger.warning(f'youtube api returned error: {response}')
            self.get_yt_data.do_not_cache()
            return None
