import json
import re
import requests

from plugin import *
from bs4 import BeautifulSoup


class crypto(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.currencies = self.get_crypto_currencies()
        self.regex = re.compile(r'^([0-9]*\.?[0-9]*)\W*([A-Za-z]+)\W+(to|in)\W+([A-Za-z]+)$')
        self.coinmarketcap_url = r'https://api.coinmarketcap.com/v1/ticker/%s'
        self.google_finance_url = r'https://www.google.com/finance/converter?a=%s&from=%s&to=%s'

    class crypto_currency_id:
        def __init__(self, id, name, symbol):
            self.id = id
            self.name = name
            self.symbol = symbol

    def get_crypto_currencies(self):
        url = r'https://api.coinmarketcap.com/v1/ticker/'
        content = requests.get(url, timeout=5).content.decode('utf-8')
        raw_result = json.loads(content)
        result = []
        for entry in raw_result:
            result.append(self.crypto_currency_id(entry['id'], entry['name'], entry['symbol']))

        return result

    def get_currency_id(self, alias):
        alias = alias.lower()
        for entry in self.currencies:
            if entry.id == alias or entry.name.lower() == alias or entry.symbol.lower() == alias:
                return entry

        return None

    @command
    def crypto(self, sender_nick, msg, **kwargs):
        if not msg: return
        msg = msg.strip()
        convert = self.regex.findall(msg)
        if convert:
            self.convert_impl(sender_nick, float(convert[0][0]) if convert[0][0] else 1., convert[0][1], convert[0][3])
        else:
            self.get_crypto_data(sender_nick, msg)

    def get_crypto_data(self, sender_nick, curr):
        self.logger.info('%s asked coinmarketcap about %s' % (sender_nick, curr))
        curr_id = self.get_currency_id(curr)

        if not curr_id:
            self.bot.say('no known currency: %s' % curr)
            return

        content = requests.get(self.coinmarketcap_url % curr_id.id, timeout=5).content.decode('utf-8')
        raw_result = json.loads(content)[0]

        hour_change = float(raw_result['percent_change_1h'])
        day_change = float(raw_result['percent_change_24h'])
        week_change = float(raw_result['percent_change_7d'])

        hour_change = color.light_green('+%s%%' % hour_change) if hour_change >= 0 else color.light_red('%s%%' % hour_change)
        day_change = color.light_green('+%s%%' % day_change) if day_change >= 0 else color.light_red('%s%%' % day_change)
        week_change = color.light_green('+%s%%' % week_change) if week_change >= 0 else color.light_red('%s%%' % week_change)

        self.bot.say(color.orange('[%s]' % curr_id.name) + ' $%s' % raw_result['price_usd'] + ' [%s hourly, %s daily, %s weekly]' % (hour_change, day_change, week_change))

    # --------------------------------------------------------------------------------------------------------------

    class convertion:
        def __init__(self, amount_from, from_curr, amount_to, to_curr):
            self.amount_from = float(amount_from)
            self.from_curr = from_curr.upper()
            self.amount_to = float(amount_to)
            self.to_curr = to_curr.upper()

        def __repr__(self):
            return '%s %s == %s %s' % (self.amount_from, self.from_curr, self.amount_to, self.to_curr)

    def convert_impl(self, sender_nick, amount, from_curr, to_curr):
        self.logger.info('%s wants to convert %s %s to %s' % (sender_nick, amount, from_curr, to_curr))
        to_curr_org = to_curr
        _from_curr = self.get_currency_id(from_curr)
        _to_curr = self.get_currency_id(to_curr)
        convertions = [None, None, None]

        if _from_curr:
            content = requests.get(self.coinmarketcap_url % _from_curr.id, timeout=5).content.decode('utf-8')
            from_curr_usd_price = float(json.loads(content)[0]['price_usd'])
            convertions[0] = self.convertion(amount, _from_curr.symbol, amount * from_curr_usd_price, 'usd')
            amount *= from_curr_usd_price
            from_curr = 'usd'

        if _to_curr:
            content = requests.get(self.coinmarketcap_url % _to_curr.id, timeout=5).content.decode('utf-8')
            to_curr_usd_price = float(json.loads(content)[0]['price_usd'])
            convertions[1] = self.convertion(amount / to_curr_usd_price, _to_curr.symbol, amount, 'usd')
            amount /= to_curr_usd_price
            to_curr = 'usd'
        else: to_curr_org = to_curr_org.upper()

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
