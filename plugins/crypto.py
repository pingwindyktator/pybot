import json
import requests

from plugin import *


class crypto(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.currencies = self.get_currencies()

    class currency_id:
        def __init__(self, id, name, symbol):
            self.id = id
            self.name = name
            self.symbol = symbol

    def get_currencies(self):
        url = r'https://api.coinmarketcap.com/v1/ticker/'
        content = requests.get(url, timeout=5).content.decode('utf-8')
        raw_result = json.loads(content)
        result = []
        for entry in raw_result:
            result.append(self.currency_id(entry['id'], entry['name'], entry['symbol']))

        return result

    def get_currency_id(self, alias):
        alias = alias.lower()
        for entry in self.currencies:
            if entry.id == alias or entry.name.lower() == alias or entry.symbol.lower() == alias:
                return entry

        return None

    @command
    def crypto(self, sender_nick, args, **kwargs):
        if not args: return
        ask = args[0]
        self.logger.info('%s asked coinmarketcap about %s' % (sender_nick, ask))
        url = r'https://api.coinmarketcap.com/v1/ticker/%s'
        ask_id = self.get_currency_id(ask)

        if not ask_id:
            self.bot.say('no known currency: %s' % ask)
            return

        content = requests.get(url % ask_id.id, timeout=5).content.decode('utf-8')
        raw_result = json.loads(content)[0]
        self.bot.say(color.orange('[%s]' % ask_id.name) + '$%s' % raw_result['price_usd'])
