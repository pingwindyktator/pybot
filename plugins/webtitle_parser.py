import re
import requests

from lxml.html import fromstring
from plugin import *


class webtitle_parser(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    def on_pubmsg(self, msg, **kwargs):
        url = msg.strip().split()[0]

        try:
            regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)

            if regex.findall(url):
                req = requests.get(url, timeout=5)
                tree = fromstring(req.content)
                title = tree.findtext('.//title')
                if title is not None and title != '':
                    self.bot.send_response_to_channel(color.light_green(title))
        except (requests.HTTPError, requests.ConnectionError, requests.RequestException):
            self.logger.info('possibly invalid URL: %s', url)
        except Exception as e:
            self.logger.error('exception caught: %s', e)
