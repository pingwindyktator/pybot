import json
import requests
import urllib.parse
import xml.etree.ElementTree

from plugin import *


class crypto_wa_warner:
    def __init__(self, bot):
        self.bot = bot
        self.known_crypto_currencies = self.get_crypto_currencies()
        self.convert_regex = re.compile(r'^([0-9]*\.?[0-9]*)\W*([A-Za-z]+)\W+(to|in)\W+([A-Za-z]+)$')

    def handle_msg(self, msg):
        msg = msg.strip()
        c = self.convert_regex.findall(msg)
        c = c[0] if c else []
        _from = c[1] if len(c) > 1 else ''
        to = c[3] if len(c) > 3 else ''
        if self.is_any_currency_known([_from, to, msg]):
            prefix = color.orange("[WARNING] ")
            suffix = ''

            if 'crypto' in self.bot.get_plugins_names() and 'crypto' in self.bot.get_plugin_commands('crypto'):
                fixed_command = f'crypto {msg}'
                suffix = f', you may try {self.bot.config["command_prefix"]}{fixed_command}'
                self.bot.register_fixed_command(fixed_command)

            self.bot.say(f'{prefix}Wolfram-Alpha seems not to handle cryptocurrencies properly{suffix}')
            return True

        return False

    def get_crypto_currencies(self):
        url = r'https://api.coinmarketcap.com/v1/ticker/'
        content = requests.get(url, timeout=10).content.decode('utf-8')
        raw_result = json.loads(content)
        result = []
        for entry in raw_result:
            result.append(self.currency_id(entry['id'], entry['name'], entry['symbol']))

        return result

    def is_any_currency_known(self, aliases):
        aliases = [a.casefold() for a in aliases]

        for alias in aliases:
            for entry in self.known_crypto_currencies:
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
                        r'&excludepodid=Sequence'

    @doc('wa <ask>: ask Wolfram|Alpha about <ask>')
    @command
    def wa(self, msg, sender_nick, **kwargs):
        self.logger.info(f'{sender_nick} asked wolfram alpha "{msg}"')
        if self.config['warn_crypto_asks']: self.crypto_warner.handle_msg(msg)
        ask = urllib.parse.quote(msg)
        raw_response = requests.get(self.full_req % (ask, self.config['api_key'])).content.decode('utf-8')
        self.manage_api_response(raw_response, msg)

    def manage_api_response(self, raw_response, ask):
        xml_root = xml.etree.ElementTree.fromstring(raw_response)
        answers = []

        if xml_root.attrib['error'] == 'true':  # wa error
            error_msg = xml_root.find('error').find('msg').text
            self.logger.warning(f'wolfram alpha error: {error_msg}')
            self.bot.say(error_msg)
            return

        if xml_root.attrib['success'] == 'false':  # no response
            self.logger.debug('******* NO DATA PARSED FROM WA RESPONSE *******')
            self.logger.debug(raw_response)
            self.logger.debug('***********************************************')
            self.bot.say_err(ask)
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
            self.bot.say_err(ask)
            return

        answers = sorted(answers)

        for it in range(0, len(answers)):
            if it > 0 and not answers[it].primary: break
            prefix = color.orange(f'[{answers[it].title}] ')
            for subpod in answers[it].subpods:
                result = prefix
                if subpod.title:
                    result = result + subpod.title + ': '

                result = result + subpod.plaintext
                self.bot.say(result)

    class wa_subpod:
        def __init__(self, plaintext, title=''):
            self.title = title.strip()
            self.plaintext = plaintext.strip().replace('  ', ' ').replace('\n', ' :: ').replace('\t', ' ').replace('|', '-')

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
