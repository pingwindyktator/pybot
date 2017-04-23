import re
import requests

from lxml.html import fromstring
from plugin import *


class webtitle_parser(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    def on_pubmsg(self, msg, **kwargs):
        urls = msg.strip().split()
        regex = re.compile(
            r'^(?:http)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        for url in urls: self.parse_url(url, regex)

    def parse_url(self, url, regex):
        try:
            if regex.findall(url):
                req = requests.get(url, timeout=5)
                tree = fromstring(req.content)
                title = tree.findtext('.//title')
                if title is not None and title != '':
                    self.bot.send_response_to_channel(color.light_green(title))

        except Exception:
            self.logger.info('possibly invalid URL: %s', url)
