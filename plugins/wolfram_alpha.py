import requests
import urllib.parse
import xml.etree.ElementTree

from threading import RLock
from datetime import timedelta
from plugin import *


class crypto_wa_warner:
    def __init__(self, bot):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bot = bot
        self.convert_regex = re.compile(r'^([0-9]*\.?[0-9]*)\W*([A-Za-z]+)\W+(to|in)\W+([A-Za-z]+)$')
        self.known_cryptocurrencies = []
        self.known_cryptocurrencies_lock = RLock()

    def handle_msg(self, msg):
        self._update_known_cryptocurrencies()
        msg = msg.strip()
        c = self.convert_regex.findall(msg)
        c = c[0] if c else []
        _from = c[1] if len(c) > 1 else ''
        to = c[3] if len(c) > 3 else ''
        if self._is_any_currency_known((_from, to, msg)):
            prefix = color.orange("[WARNING] ")
            suffix = ''

            if 'crypto' in self.bot.get_plugins_names() and 'crypto' in self.bot.get_plugin_commands('crypto'):
                fixed_command = f'crypto {msg}'
                suffix = f', you may try {self.bot.get_command_prefix()}{fixed_command}'
                self.bot.register_fixed_command(fixed_command)

            self.bot.say(f'{prefix}Wolfram-Alpha seems not to handle cryptocurrencies properly{suffix}')
            return True

        return False

    @utils.timed_lru_cache(expiration=timedelta(hours=1))
    def _update_known_cryptocurrencies(self):
        self.logger.debug('updating known cryptocurrencies...')
        url = r'https://api.coinmarketcap.com/v1/ticker/?limit=0'
        raw_result = requests.get(url, timeout=10).json()
        known_crypto_currencies = []
        for entry in raw_result:
            known_crypto_currencies.append(self.currency_id(entry['id'], entry['name'], entry['symbol']))

        with self.known_cryptocurrencies_lock:
            self.known_cryptocurrencies = known_crypto_currencies
            self._is_any_currency_known.clear_cache()

    @utils.timed_lru_cache(typed=True)
    def _is_any_currency_known(self, _aliases):
        aliases = [a.casefold() for a in _aliases]

        with self.known_cryptocurrencies_lock:
            for alias in aliases:
                for entry in self.known_cryptocurrencies:
                    if entry.id.casefold() == alias or entry.name.casefold() == alias or entry.symbol.casefold() == alias:
                        return True

            return False

    class currency_id:
        def __init__(self, id, name, symbol):
            self.id = id
            self.name = name
            self.symbol = symbol


class wolfram_alpha(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.crypto_warner = crypto_wa_warner(bot)
        units = 'nonmetric' if self.config['nonmetric_units'] else 'metric'
        self.full_req = r'http://api.wolframalpha.com/v2/query?' \
                        r'input=%s' \
                        r'&appid=%s' \
                        r'&format=plaintext' \
                        r'&scantimeout=3.0' \
                        r'&podtimeout=4.0' \
                        r'&formattimeout=8.0' \
                        r'&parsetimeout=5.0' \
                        r'&units=' + units + \
                        r'&excludepodid=SeriesRepresentations:*' \
                        r'&excludepodid=Illustration' \
                        r'&excludepodid=TypicalHumanComputationTimes' \
                        r'&excludepodid=NumberLine' \
                        r'&excludepodid=NumberName' \
                        r'&excludepodid=Input' \
                        r'&excludepodid=DifferenceConversions' \
                        r'&excludepodid=Sequence'

    @doc('wa <ask>: ask Wolfram|Alpha about <ask>')
    @command
    @command_alias('wolfram_alpha', 'wolfram')
    def wa(self, msg, sender_nick, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked wolfram alpha "{msg}"')
        if self.config['warn_crypto_asks']: self.crypto_warner.handle_msg(msg)
        ask = urllib.parse.quote(msg)
        self.manage_api_response(self.get_api_response(ask))

    @utils.timed_lru_cache(expiration=timedelta(hours=1), typed=True)
    def get_api_response(self, ask):
        raw_response = requests.get(self.full_req % (ask, self.config['api_key'])).content.decode()
        xml_root = xml.etree.ElementTree.fromstring(raw_response)
        if xml_root.attrib['error'] == 'true' or xml_root.attrib['success'] == 'false':
            self.get_api_response.do_not_cache()

        return xml_root

    def manage_api_response(self, xml_root):
        answers = []

        if xml_root.attrib['error'] == 'true':  # wa error
            error_msg = xml_root.find('error').find('msg').text
            self.logger.warning(f'wolfram alpha error: {error_msg}')
            self.bot.say(error_msg)
            return

        if xml_root.attrib['success'] == 'false':  # no response
            self.bot.say_err()
            return

        for pod in xml_root.findall('pod'):
            if pod.attrib['error'] == 'true': continue  # wa error
            title = pod.attrib['title']
            primary = 'primary' in pod.attrib and pod.attrib['primary'] == 'true'
            position = int(pod.attrib['position'])
            subpods = []

            for subpod in pod.findall('subpod'):
                plaintext = subpod.find('plaintext').text
                subtitle = subpod.attrib['title']
                if not plaintext: continue
                subpods.append(self.wa_subpod(plaintext, subtitle))

            if subpods: answers.append(self.wa_pod(title, position, subpods, primary))

        if not answers:
            self.bot.say_err()
            return

        answers = sorted(answers)

        for it in range(0, len(answers)):
            if it > 0 and not answers[it].primary: break
            prefix = color.orange(f'[{answers[it].title}] ')
            for subpod in answers[it].subpods:
                if subpod.title: prefix = prefix + subpod.title + ': '
                self.say_single_subpod(subpod.plaintext, prefix)

    def say_single_subpod(self, plaintext, prefix):
        assert not self.bot.is_msg_too_long(prefix)
        join_token = self.wa_subpod.get_join_token()
        plaintext = plaintext.split(join_token)
        to_send = ''

        while plaintext:
            maybe_to_send = join_token.join([to_send, plaintext[0]] if to_send else [plaintext[0]])  # taking next part of subpod
            if self.bot.is_msg_too_long(prefix + maybe_to_send):
                assert to_send
                self.bot.say(prefix + to_send)
                to_send = ''
            else:
                to_send = maybe_to_send
                del plaintext[0]

        if to_send: self.bot.say(prefix + to_send)

    class wa_subpod:
        def __init__(self, plaintext, title=''):
            self.title = title.strip()
            self.plaintext = plaintext.strip().replace('  ', ' ').replace('\t', ' ').replace('|', '-').split('\n')
            self.plaintext = list(filter(lambda e: e != '...', self.plaintext))  # remove all '...' from self.plaintext
            self.plaintext = self.get_join_token().join(self.plaintext)

        @staticmethod
        def get_join_token():
            return ' :: '

    class wa_pod:
        def __init__(self, title, position, subpods, primary=False):
            self.title = title.strip()
            self.position = position
            self.subpods = subpods
            self.primary = primary

        def __lt__(self, other):
            if self.primary and not other.primary: return True
            if other.primary and not self.primary: return False
            return self.position < other.position
