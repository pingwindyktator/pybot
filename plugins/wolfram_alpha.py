import requests

from plugin import *
import urllib.parse


class wolfram_alpha(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def wa(self, msg, sender_nick, **kwargs):
        key = '4EU37Y-TX9WJG3JH3'  # should be replaced with you'r personal API key
        short_req = r'https://api.wolframalpha.com/v1/result?i=%s&appid=%s'
        full_req = 'https://www.wolframalpha.com/input/?i=%s'

        self.logger.info('%s asked wolfram alpha of %s' % (sender_nick, msg))
        ask = self.parse_to_url(msg)
        response = requests.get(short_req % (ask, key), timeout=5).content.decode('utf-8')
        response = color.orange('[Wolfram|Alpha] ') + response
        if response.lower().strip() == ask.lower().strip():
            response = full_req % ask

        self.bot.say(response)

    @staticmethod
    def parse_to_url(str):
        return urllib.parse.quote(str)
