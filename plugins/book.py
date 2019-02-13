import urllib.parse
import requests
import xml.etree.ElementTree

from datetime import timedelta
from plugin import *


class book(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.goodreads_api_uri = r'https://www.goodreads.com/search.xml?key=%s&q=%s'

    @utils.timed_lru_cache(expiration=timedelta(hours=1), typed=True)
    def get_api_response(self, ask):
        raw_response = requests.get(self.goodreads_api_uri % (self.config['goodreads_api_key'], ask)).content.decode()
        return xml.etree.ElementTree.fromstring(raw_response)

    @command
    @doc('get book info from goodreads.com')
    def book(self, sender_nick, msg, **kwargs):
        if not msg: return
        msg = msg.strip()
        ask = urllib.parse.quote(msg)
        self.logger.info(f'{sender_nick} asked goodreads.com "{msg}"')
        xml_root = self.get_api_response(ask)

        result = xml_root.find('search').find('results')
        if len(result) == 0:
            self.bot.say_err(msg)
            return

        result = xml_root.find('search').find('results')[0]
        rating = self.get_text_or_none(result.find('average_rating'))
        rating_count = self.get_text_or_none(result.find('ratings_count'))
        year = self.get_text_or_none(result.find('original_publication_year'))

        result = result.find('best_book')
        author = result.find('author')
        author = self.get_text_or_none(author.find('name'))
        title = self.get_text_or_none(result.find('title'))
        id = self.get_text_or_none(result.find('id'))

        if not title or not id:
            self.bot.say_err()
            return

        prefix = f'[{title}'
        if year: prefix += f' ({year})'
        if author: prefix += f' by {author}'
        prefix += ']'
        prefix = color.orange(prefix)

        response = r'https://www.goodreads.com/book/show/%s' % id
        if rating:
            response += f' ({rating}/5'
            if rating_count: response += f' out of {rating_count} voters'
            response += ')'

        self.bot.say(f'{prefix} {response}')

    def get_text_or_none(self, xml_el):
        if xml_el is None: return None
        if 'nil' in xml_el.attrib and xml_el.attrib['nil'] == 'true': return None
        if not xml_el.text: return None
        return xml_el.text
