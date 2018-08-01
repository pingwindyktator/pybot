import os
import re
import sqlite3

from datetime import timedelta
from threading import Lock
from plugin import *


class words_blacklist(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = "blacklist"
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (entry TEXT primary key not null)")
        self.db_mutex = Lock()

    def get_blacklist(self):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT entry FROM '{self.db_name}'")
            result = self.db_cursor.fetchall()

        return [r[0] for r in result]

    def add_to_blacklist(self, regex):
        with self.db_mutex:
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{self.db_name}' VALUES (?)", (regex,))
            self.db_connection.commit()

    def remove_from_blacklist(self, regex):
        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE entry = ?", (regex,))
            self.db_connection.commit()

    def on_pubmsg(self, source, msg, **kwargs):
        # TODO case sensitivity? add flags?

        if self.is_whitelisted(source.nick): return
        blacklist = self.get_blacklist()

        for word in blacklist:
            if re.findall(word, msg):
                if self.am_i_channel_operator():
                    self.bot.kick(source.nick, 'watch your language!')
                    self.logger.warning(f'{source.nick} kicked [{word}]')
                else:
                    self.bot.say(f'{source.nick}, watch your language!')
                    self.logger.warning(f'{source.nick} cannot be kicked [{word}], operator privileges needed')

    @command(admin=True)
    @doc('ban_word <regex>: ban <regex>. When it appears on chat, bot will kick its sender')
    def ban_word(self, sender_nick, msg, **kwargs):
        if not msg: return
        try:
            re.compile(msg)
        except Exception:
            self.bot.say(f'it does not look like a valid regex pattern')
            return

        suffix = ', but I need operator privileges to kick ;(' if not self.am_i_channel_operator() else ''
        self.add_to_blacklist(msg)

        self.bot.say(f'"{msg}" banned{suffix}')
        self.logger.info(f'regex "{msg}" banned by {sender_nick}')

    @command(admin=True)
    @doc('unban_word <regex>: unban <regex>')
    def unban_word(self, sender_nick, msg, **kwargs):
        self.remove_from_blacklist(msg)

        self.bot.say_ok()
        self.logger.info(f'regex "{msg}" unbanned by {sender_nick}')

    @command
    @doc('get banned regexps')
    def blacklist(self, sender_nick, **kwargs):
        blacklist = self.get_blacklist()
        self.logger.info(f'{sender_nick} asks for blacklist: {blacklist}')

        if blacklist:
            self.bot.say(f'banned regexps: {blacklist}')
        else:
            self.bot.say(f'no banned regexps')

    def am_i_channel_operator(self):
        return self.bot.get_channel().is_oper(self.bot.get_nickname())

    @utils.timed_lru_cache(expiration=timedelta(seconds=5), typed=True)
    def is_whitelisted(self, sender_nick):
        if self.bot.is_user_op(sender_nick): return True
        if self.bot.get_channel().is_oper(sender_nick): return True
        if self.bot.get_channel().is_voiced(sender_nick): return True

        return False
