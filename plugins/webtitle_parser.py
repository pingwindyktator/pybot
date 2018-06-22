import re
import requests

from lxml.html import fromstring
from plugin import *


@doc('parse URL to get webpage title')
class webtitle_parser(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.regex = re.compile(
            r'^(?:http)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def on_pubmsg(self, msg, source, **kwargs):
        if self.bot.is_user_ignored(source.nick): return

        urls = msg.strip().split()
        for url in urls: self.parse_url(url.strip())

    def parse_url(self, url):
        try:
            if self.regex.findall(url):
                req = requests.get(url, timeout=5)
                tree = fromstring(req.content.decode())
                title = tree.findtext('.//title').strip()
                if title is not None and title != '':
                    self.bot.say(color.light_green(title))

        except Exception:
            self.logger.info(f'possibly invalid URL: {url}')
