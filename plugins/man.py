import requests

from datetime import timedelta
from bs4 import BeautifulSoup
from plugin import *


class man(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.man_url = r'http://man.he.net/?topic=%s&section=all'

    @command
    @doc('man <command>: get unix manual entry for <command> from man.he.net')
    def man(self, sender_nick, args, **kwargs):
        if not args: return
        ask = args[0].strip().casefold()
        if ask == 'df':
            self.man_df()
            return

        url = self.man_url % ask
        self.logger.info(f'{sender_nick} asked for man of {ask}')

        content = self.get_api_response(ask)
        start = content.find(b'DESCRIPTION\n')
        end = content.find(b'\n\n', start)
        if start == -1 or end == -1:
            self.bot.say_err(ask)
            return

        result = content[start + len('DESCRIPTION'):end].replace(b'       ', b'').replace(b'-\n', b'').replace(b'\n', b' ').replace(b'  ', b' ').replace(b'  ', b' ').replace(b'  ', b' ').decode('utf-8').strip()

        if self.bot.is_msg_too_long(result):
            self.bot.say(result, sender_nick)
        else:
            self.bot.say(color.orange(f'[{ask}] ') + result)

        self.bot.say(color.orange(f'[{ask}] ') + url)

    @utils.timed_lru_cache(timedelta(hours=1), typed=True)
    def get_api_response(self, ask):
        content = requests.get(self.man_url % ask, timeout=5).content
        return BeautifulSoup(content, 'lxml').text.encode('utf-8')

    def man_df(self):
        answer = 'Dwarf Fortress is a part construction and management simulation, part roguelike, indie video game created by Tarn and Zach Adams. The primary game mode is set in a procedurally generated fantasy world in which the player indirectly controls a group of dwarves, and attempts to construct a successful and wealthy underground fortress.'
        self.bot.say(color.orange(f'[df] ') + answer)
        self.bot.say(color.orange(f'[df] ') + r'http://askubuntu.com/questions/938606/dwarf-fortress-starting-during-apt-get-upgrade')
