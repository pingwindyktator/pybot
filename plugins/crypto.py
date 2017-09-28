import json
import re
from datetime import timedelta
from threading import Timer

import requests

from plugin import *


class crypto(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.known_crypto_currencies = self.get_crypto_currencies()
        self.convert_regex = re.compile(r'^([0-9]*\.?[0-9]*)\W*([A-Za-z]+)\W+(to|in)\W+([A-Za-z]+)$')
        self.time_delta_regex = re.compile(r'([0-9]+[Hh])?\W*([0-9]+[Mm])?(.*)')
        self.coinmarketcap_url = r'https://api.coinmarketcap.com/v1/ticker/%s'
        self.fixer_url = r'http://api.fixer.io/latest?base=%s'
        self.watch_timers = {}  # {curr -> watch_desc}

    class watch_desc:
        def __init__(self, timer_object, timedelta):
            self.timer_object = timer_object
            self.timedelta = timedelta

    class currency_id:
        def __init__(self, id, name, symbol):
            self.id = id
            self.name = name
            self.symbol = symbol

    class currency_info:
        def __init__(self, id, raw_result):
            self.id = id
            self.price_usd = float(raw_result['price_usd']) if raw_result['price_usd'] else None
            self.price_btc = float(raw_result['price_btc']) if raw_result['price_btc'] else None
            self.hour_change = float(raw_result['percent_change_1h']) if raw_result['percent_change_1h'] else None
            self.day_change = float(raw_result['percent_change_24h']) if raw_result['percent_change_24h'] else None
            self.week_change = float(raw_result['percent_change_7d']) if raw_result['percent_change_7d'] else None
            self.marker_cap_usd = float(raw_result['market_cap_usd']) if raw_result['market_cap_usd'] else None

    def unload_plugin(self):
        for t in self.watch_timers.values():
            t.timer_object.cancel()

    def get_crypto_currencies(self):
        url = r'https://api.coinmarketcap.com/v1/ticker/'
        content = requests.get(url, timeout=10).content.decode('utf-8')
        raw_result = json.loads(content)
        result = []
        for entry in raw_result:
            result.append(self.currency_id(entry['id'], entry['name'], entry['symbol']))

        return result

    def get_crypto_currency_id(self, alias):
        alias = alias.lower()
        for entry in self.known_crypto_currencies:
            if entry.id.lower() == alias or entry.name.lower() == alias or entry.symbol.lower() == alias:
                return entry

        return None

    def get_crypto_curr_info(self, curr):
        curr_id = self.get_crypto_currency_id(curr)
        if not curr_id: return None

        content = requests.get(self.coinmarketcap_url % curr_id.id, timeout=10).content.decode('utf-8')
        raw_result = json.loads(content)[0]
        return self.currency_info(curr_id, raw_result)

    def generate_curr_price_change_output(self, curr_info):
        result = ''

        for change, change_str in zip([curr_info.hour_change, curr_info.day_change, curr_info.week_change], ['hourly', 'daily', 'weekly']):
            if change:
                change_price = curr_info.price_usd - (curr_info.price_usd / (1 + change / 100.)) if curr_info.price_usd else None
                if change >= 0:
                    subresult = color.light_green(f'+{change}%')
                    if change_price: subresult = subresult + ' | ' + color.light_green(f'+${change_price:.2f}')
                else:
                    subresult = color.light_red(f'{change}%')
                    if change_price: subresult = subresult + ' | ' + color.light_red('-$%.2f' % abs(change_price))

                result = f'{result}[{subresult} {change_str}] '

        return result.strip()

    @command
    @doc("""crypto <currency>: get information about <currency> cryptocurrency (updated every 1 hour from coinmarketcap)
            crypto <amount> <currency_from> to <currency_to>: convert <amount> of <currency_from> to <currency_to> (based on coinmarketcap and fixer.io)""")
    def crypto(self, sender_nick, msg, **kwargs):
        if not msg: return
        msg = msg.strip()
        convert = self.convert_regex.findall(msg)

        if convert:
            amount = float(convert[0][0]) if convert[0][0] else 1.
            self.logger.info(f'{sender_nick} wants to convert {amount} {convert[0][1]} to {convert[0][3]}')
            self.convert_impl(amount, convert[0][1], convert[0][3])
        else:
            self.logger.info(f'{sender_nick} asked coinmarketcap about {msg}')
            self.crypto_impl(msg)

    def crypto_impl(self, curr):
        curr_info = self.get_crypto_curr_info(curr)

        if not curr_info:
            self.bot.say_err(curr)
            return

        price_usd = f' ${curr_info.price_usd} (US dollars) ' if curr_info.price_usd else ' unknown price '
        self.bot.say(color.orange(f'[{curr_info.id.name}]') + price_usd + self.generate_curr_price_change_output(curr_info))

    # --------------------------------------------------------------------------------------------------------------

    class convertion:
        def __init__(self, amount_from, from_curr, amount_to, to_curr):
            self.amount_from = float(amount_from)
            self.from_curr = from_curr
            self.amount_to = float(amount_to)
            self.to_curr = to_curr

        def __repr__(self):
            return f'{self.amount_from} {self.from_curr} == {self.amount_to} {self.to_curr}'

    def convert_impl(self, amount, from_curr, to_curr):
        to_curr_org = to_curr.upper()
        _from_curr = self.get_crypto_curr_info(from_curr)
        _to_curr = self.get_crypto_curr_info(to_curr)
        convertions = [None, None, None]

        if _from_curr:
            if not _from_curr.price_usd:
                self.bot.say(f'unknown price of {from_curr}')
                return

            convertions[0] = self.convertion(amount, _from_curr.id.symbol, amount * _from_curr.price_usd, 'usd')
            amount *= _from_curr.price_usd
            from_curr = 'usd'

        if _to_curr:
            if not _to_curr.price_usd:
                self.bot.say(f'unknown price of {to_curr}')
                return

            convertions[1] = self.convertion(amount / _to_curr.price_usd, _to_curr.id.symbol, amount, 'usd')
            amount /= _to_curr.price_usd
            to_curr = 'usd'
            to_curr_org = _to_curr.id.symbol

        result = amount

        if not (_from_curr and _to_curr) and from_curr.upper() != to_curr.upper():
            content = requests.get(self.fixer_url % from_curr, timeout=5).content.decode('utf-8')
            raw_result = json.loads(content)
            if 'error' in raw_result:
                if raw_result['error'] == 'Invalid base':
                    self.bot.say_err(from_curr)
                else:
                    self.bot.say(f"fixer.io can't convert {from_curr} to {to_curr}")
                    self.logger.warning(f'fixer.io error: {raw_result["error"]}')
                return
            elif to_curr.upper() not in raw_result['rates']:
                self.bot.say_err(to_curr)
                return
            else:
                result = amount * raw_result['rates'][to_curr.upper()]
                convertions[2] = self.convertion(amount, from_curr, result, to_curr)

        self.logger.info(convertions)
        self.bot.say(color.orange('[Result]') + f' {result} {to_curr_org}')

    # --------------------------------------------------------------------------------------------------------------

    @command
    @doc('crypto_watch <crypto_currency> <time>: watches <crypto_currency> every <time> time. <time> should be %H:%M  (eg.  1h 42m)')
    def crypto_watch(self, sender_nick, msg, **kwargs):
        if not msg: return
        curr = msg.split()[0]
        curr_id = self.get_crypto_currency_id(curr)
        reg_res = self.time_delta_regex.findall(msg[len(curr):].strip())
        if not reg_res: return
        hours = int(reg_res[0][0][:-1]) if reg_res[0][0] else 0
        minutes = int(reg_res[0][1][:-1]) if reg_res[0][1] else 0
        if hours == 0 and minutes == 0: return

        if not curr_id:
            self.bot.say_err(curr)
            return

        if curr_id.id in self.watch_timers:
            self.logger.info(f'removed previous crypto watch for {curr_id.id}')
            self.watch_timers[curr_id.id].timer_object.cancel()

        delta_time = timedelta(hours=hours, minutes=minutes).total_seconds()
        t = Timer(delta_time, self.watch_say, kwargs={'curr': curr_id.id})
        wd = self.watch_desc(t, delta_time)
        self.watch_timers[curr_id.id] = wd
        t.start()
        self.bot.say_ok()
        self.logger.info(f'{sender_nick} sets crypto watch: {curr_id.id}: {delta_time}s')

    @command
    @doc('stop_crypto_watch <crypto_currency>: stops watching <crypto_currency>')
    def stop_crypto_watch(self, sender_nick, args, **kwargs):
        if not args: return
        curr = args[0]
        curr_id = self.get_crypto_currency_id(curr)
        if not curr_id:
            self.bot.say_err(curr)
            return

        if curr_id.id not in self.watch_timers:
            self.bot.say(f'no watch set for {curr_id.id}')
            return

        self.watch_timers[curr_id.id].timer_object.cancel()
        del self.watch_timers[curr_id.id]
        self.logger.info(f'{sender_nick} removes crypto watch: {curr_id.id}')
        self.bot.say_ok()

    def watch_say(self, curr):
        if curr not in self.watch_timers:
            self.logger.error(f'no such currency in crypto_watch memory: {curr}')
            raise RuntimeError(f'no such currency in crypto_watch memory: {curr}')

        self.crypto_impl(curr)
        t = Timer(self.watch_timers[curr].timedelta, self.watch_say, kwargs={'curr': curr})
        self.watch_timers[curr].timer_object = t
        t.start()
