import json
import re
import requests

from plugin import *
from bs4 import BeautifulSoup


class crypto(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.known_crypto_currencies = self.get_crypto_currencies()
        self.convert_regex = re.compile(r'^([0-9]*\.?[0-9]*)\W*([A-Za-z]+)\W+(to|in)\W+([A-Za-z]+)$')
        self.coinmarketcap_url = r'https://api.coinmarketcap.com/v1/ticker/%s'
        self.google_finance_url = r'https://www.google.com/finance/converter?a=%s&from=%s&to=%s'

    class currency_id:
        def __init__(self, id, name, symbol):
            self.id = id
            self.name = name
            self.symbol = symbol

    class currency_info:
        def __init__(self, id, raw_result):
            self.id = id
            self.price_usd = float(raw_result['price_usd'])
            self.price_btc = float(raw_result['price_btc'])
            self.hour_change = float(raw_result['percent_change_1h'])
            self.day_change = float(raw_result['percent_change_24h'])
            self.week_change = float(raw_result['percent_change_7d'])
            self.marker_cap_usd = float(raw_result['market_cap_usd'])

    def get_crypto_currencies(self):
        url = r'https://api.coinmarketcap.com/v1/ticker/'
        content = requests.get(url, timeout=5).content.decode('utf-8')
        raw_result = json.loads(content)
        result = []
        for entry in raw_result:
            result.append(self.currency_id(entry['id'], entry['name'], entry['symbol']))

        return result

    def get_crypto_currency_id(self, alias):
        alias = alias.lower()
        for entry in self.known_crypto_currencies:
            if entry.id == alias or entry.name.lower() == alias or entry.symbol.lower() == alias:
                return entry

        return None

    def get_crypto_curr_info(self, curr):
        curr_id = self.get_crypto_currency_id(curr)
        if not curr_id: return None

        content = requests.get(self.coinmarketcap_url % curr_id.id, timeout=5).content.decode('utf-8')
        raw_result = json.loads(content)[0]
        return self.currency_info(curr_id, raw_result)

    def generate_curr_price_change_output(self, curr_info):
        results = []

        for change in [curr_info.hour_change, curr_info.day_change, curr_info.week_change]:
            if change >= 0:
                result = color.light_green('+%s%%' % change) + ' | ' + color.light_green('+$%.2f' % (change * curr_info.price_usd / 100.))
            else:
                result = color.light_red('%s%%' % change) + ' | ' + color.light_red('-$%.2f' % abs(change * curr_info.price_usd / 100.))

            results.append(result)

        return '[%s hourly] [%s daily] [%s weekly]' % (results[0], results[1], results[2])

    @command
    def crypto(self, sender_nick, msg, **kwargs):
        if not msg: return
        msg = msg.strip()
        convert = self.convert_regex.findall(msg)

        if convert:
            self.logger.info('%s wants to convert %s %s to %s' % (sender_nick, convert[0][0], convert[0][1], convert[0][3]))
            self.convert_impl(float(convert[0][0]) if convert[0][0] else 1., convert[0][1], convert[0][3])
        else:
            self.logger.info('%s asked coinmarketcap about %s' % (sender_nick, msg))
            self.crypto_impl(msg)

    def crypto_impl(self, curr):
        curr_info = self.get_crypto_curr_info(curr)

        if not curr_info:
            self.bot.say('no such crypto currency: %s' % curr)
            return

        self.bot.say(color.orange('[%s]' % curr_info.id.name) + ' $%s (US dollars) ' % curr_info.price_usd + self.generate_curr_price_change_output(curr_info))

    # --------------------------------------------------------------------------------------------------------------

    class convertion:
        def __init__(self, amount_from, from_curr, amount_to, to_curr):
            self.amount_from = float(amount_from)
            self.from_curr = from_curr
            self.amount_to = float(amount_to)
            self.to_curr = to_curr

        def __repr__(self):
            return '%s %s == %s %s' % (self.amount_from, self.from_curr, self.amount_to, self.to_curr)

    def convert_impl(self, amount, from_curr, to_curr):
        to_curr_org = to_curr.upper()
        _from_curr = self.get_crypto_curr_info(from_curr)
        _to_curr = self.get_crypto_curr_info(to_curr)
        convertions = [None, None, None]

        if _from_curr:
            convertions[0] = self.convertion(amount, _from_curr.id.symbol, amount * _from_curr.price_usd, 'usd')
            amount *= _from_curr.price_usd
            from_curr = 'usd'

        if _to_curr:
            convertions[1] = self.convertion(amount / _to_curr.price_usd, _to_curr.id.symbol, amount, 'usd')
            amount /= _to_curr.price_usd
            to_curr = 'usd'
            to_curr_org = _to_curr.id.symbol

        result = amount

        if not (_from_curr and _to_curr):
            content = requests.get(self.google_finance_url % (amount, from_curr, to_curr), timeout=5).content
            soup = BeautifulSoup(content, "lxml")
            div = soup.find('div', {'id': 'currency_converter_result'})
            if not div.contents[1].contents:
                self.bot.say("Google Finances can't convert %s %s to %s" % (amount, from_curr, to_curr))
                return
            else:
                result = float(div.contents[1].contents[0].split()[0])
                convertions[2] = self.convertion(amount, from_curr, result, to_curr)

        self.logger.info(convertions)
        self.bot.say(color.orange('[Result]') + ' %s %s' % (result, to_curr_org))
