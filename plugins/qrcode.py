import urllib.parse
import requests

from plugin import *


class qrcode(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @doc('qrcode <text>: get qrcode of <text>')
    def qrcode(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} want a qrcode of {msg}')
        msg = urllib.parse.quote(msg)
        link = r'http://chart.googleapis.com/chart?cht=qr&chs=400x400&chl=%s' % msg
        short_link = self.try_shorten(link)
        self.bot.say(short_link if short_link else link)

    def try_shorten(self, url):
        raw_response = requests.get(r'https://is.gd/create.php?format=simple&url=%s' % urllib.parse.quote(url))
        if raw_response.status_code == requests.codes.ok and raw_response.content:
            return raw_response.content.decode()

        return None
