import requests

from datetime import timedelta, datetime
from plugin import *


class niedziela(plugin):
    @utils.timed_lru_cache(expiration=timedelta(minutes=10))
    def get_result(self):
        result = requests.get(
            r'https://jakitydzien.pl/api/?type=json&include_sunday_type=true&api_key=cb01cde96fa2e2ddd437656a92c2da98',
            timeout=10).json()

        return not result['niedziela'] == 'niehandlowa'

    @command
    @doc('answers whether trading is disallowed next Sunday in Poland')
    def niedziela(self, **kwargs):
        result_str = 'kapitalistyczna' if self.get_result() else 'komunistyczna'
        self.bot.say(f'Niedziela {utils.get_next_weekday_datetime(datetime.now(), 6).strftime("%Y-%m-%d")} jest {result_str}.')
