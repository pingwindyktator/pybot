import json
import requests

from datetime import timedelta
from threading import Timer, Lock
from plugin import *


class crypto(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.known_crypto_currencies = None
        self.convert_regex = re.compile(r'^([0-9]*\.?[0-9]*)\W*([A-Za-z]+)\W+(to|in)\W+([A-Za-z]+)$')
        self.time_delta_regex = re.compile(r'([0-9]+[Hh])?\W*([0-9]+[Mm])?(.*)')
        self.watch_timers = {}  # {curr -> watch_desc}
        self.crypto_currencies_lock = Lock()

    def unload_plugin(self):
        for t in self.watch_timers.values():
            t.timer_object.cancel()

    @utils.timed_lru_cache(expiration=timedelta(hours=1))
    def update_known_crypto_currencies(self):
        self.logger.debug('updating known cryptocurrencies...')
        url = r'https://api.coinmarketcap.com/v1/ticker/?limit=0'
        raw_result = requests.get(url, timeout=10).json()
        result = []
        for entry in raw_result:
            result.append(self.currency_id(entry['id'], entry['name'], entry['symbol']))

        with self.crypto_currencies_lock:
            self.known_crypto_currencies = result
            self.get_crypto_currency_id.clear_cache()

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

    @utils.timed_lru_cache(typed=True)
    def get_crypto_currency_id(self, alias):
        alias = alias.casefold()
        with self.crypto_currencies_lock:
            for entry in self.known_crypto_currencies:
                if entry.id.casefold() == alias or entry.name.casefold() == alias or entry.symbol.casefold() == alias:
                    return entry

        return None

    @utils.timed_lru_cache(expiration=timedelta(minutes=3), typed=True)
    def get_crypto_curr_info(self, curr):
        self.update_known_crypto_currencies()
        curr_id = self.get_crypto_currency_id(curr)
        if not curr_id: return None
        url = r'https://api.coinmarketcap.com/v1/ticker/%s'
        raw_result = requests.get(url % curr_id.id, timeout=10).json()[0]
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

        if curr_info.price_usd > 10:
            price_usd = f' ${curr_info.price_usd:.2f} (US dollars) '
        elif curr_info.price_usd > 0:
            price_usd = f' ${curr_info.price_usd:.10f} (US dollars) '
        else:
            price_usd = ' unknown price '

        self.bot.say(color.orange(f'[{curr_info.id.name}]') + price_usd + self.generate_curr_price_change_output(curr_info))

    @command
    @doc('get information about Bitcoin (updated every 1 hour from coinmarketcap)')
    def btc(self, sender_nick, **kwargs):
        curr = 'btc'
        self.logger.info(f'{sender_nick} asked coinmarketcap about {curr}')
        self.crypto_impl(curr)

    @command
    @doc('get information about Ethereum (updated every 1 hour from coinmarketcap)')
    def eth(self, sender_nick, **kwargs):
        curr = 'eth'
        self.logger.info(f'{sender_nick} asked coinmarketcap about {curr}')
        self.crypto_impl(curr)

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
        from_curr_info = self.get_crypto_curr_info(from_curr)
        to_curr_info = self.get_crypto_curr_info(to_curr)

        if not from_curr_info:
            self.bot.say(f'unknown cryptocurrency: {from_curr}')
            return

        to_curr = to_curr_info.id.symbol.lower() if to_curr_info else to_curr.lower()
        url = r'https://api.coinmarketcap.com/v1/ticker/%s/?convert=%s' % (from_curr_info.id.id, to_curr)
        raw_result = requests.get(url, timeout=10).json()[0]

        if f'price_{to_curr}' not in raw_result:
            self.bot.say(f'cannot convert {from_curr} to {to_curr}')
            return

        result = float(raw_result[f'price_{to_curr}']) * amount

        if result > 10: result = f'{result:.2f}'
        else: result = f'{result:.10f}'

        self.bot.say(color.orange('[Result]') + f' {result} {to_curr.upper()}')

    # --------------------------------------------------------------------------------------------------------------

    @command
    @doc('crypto_watch <crypto_currency> <time>: watches <crypto_currency> every <time> time. <time> should be %H %M  (eg.  1h 42m)')
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
