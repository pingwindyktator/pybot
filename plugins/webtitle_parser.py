import re
import requests

from lxml.html import fromstring
from plugin import *
from color import Color


@doc('parse URL to get webpage title')
class webtitle_parser(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_pubmsg(self, msg, **kwargs):
        urls = msg.strip().split()
        regex = re.compile(
            r'^(?:http)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        for url in urls: self.parse_url(url.strip(), regex)

    def parse_url(self, url, regex):
        try:
            if regex.findall(url):
                req = requests.get(url, timeout=5)
                tree = fromstring(req.content)
                title = tree.findtext('.//title').strip()
                if title is not None and title != '':
                    self.bot.say(Color.light_green(title))

        except Exception:
            self.logger.info(f'possibly invalid URL: {url}')
