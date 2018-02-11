import os
import sqlite3

from threading import Lock
from plugin import *


class irc_privmsg_logger_handler(logging.StreamHandler):
    def __init__(self, bot, plhs_getter):
        super().__init__()
        self.plhs_getter = plhs_getter
        self.bot = bot
        self.ignored_funcs = ['send_raw', '_say_impl', 'say', '_process_say']

    def emit(self, record):
        if record.funcName in self.ignored_funcs: return
        try:
            msg = self.format(record)
            for target, level in self.plhs_getter().items():
                if record.levelno >= level and self.bot.is_connected():
                    force = True if record.levelno >= logging.WARNING else False
                    self.bot.say(msg, target, force)
        except Exception:
            self.handleError(record)


class privmsg_logger_handler(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.plh_handler = irc_privmsg_logger_handler(self.bot, self.get_plhs_impl)
        self.plh_handler.setFormatter(logging.Formatter('%(levelname)-10s%(filename)s:%(funcName)-16s: %(message)s'))
        self.plh_handler.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(self.plh_handler)

        self.db_name = 'plhs'
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nickname TEXT primary key not null, logging_level TEXT)")  # nickname -> logging_level
        self.db_mutex = Lock()

    def unload_plugin(self):
        logging.getLogger('').removeHandler(self.plh_handler)

    def get_plhs_impl(self):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT nickname, logging_level FROM '{self.db_name}'")
            result = self.db_cursor.fetchall()
            result = {irc_nickname(r[0]): int(r[1]) for r in result}
            return result

    @command
    @admin
    @doc('add_plh <level>: add privmsg logger handler at <level> level. bot will send you app logs in a private message')
    def add_plh(self, sender_nick, args, **kwargs):
        if not args: return
        level = args[0].strip().casefold()
        sender_nick = sender_nick

        if level not in utils.logging_level_str_to_int:
            self.bot.say(f'unknown level: {level}')
            return

        self.logger.warning(f'plh added: {sender_nick} at {level}')
        level = utils.logging_level_str_to_int[level]

        with self.db_mutex:
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{self.db_name}' VALUES (?, ?)", (sender_nick.casefold(), level))
            self.db_connection.commit()

        self.bot.say(f'plh added: {sender_nick} at {utils.int_to_logging_level_str[level]}')

    @command
    @admin
    @doc('remove saved privmsg logger handler')
    def rm_plh(self, sender_nick, **kwargs):
        if sender_nick not in self.get_plhs_impl(): return
        sender_nick = sender_nick.casefold()

        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (sender_nick,))
            self.db_connection.commit()

        self.logger.info(f'plh for {sender_nick} removed')
        self.bot.say_ok()

    @command
    @doc('get all registered privmsg logger handlers')
    def get_plhs(self, sender_nick, **kwargs):
        response = {t: utils.int_to_logging_level_str[level] for t, level in self.get_plhs_impl().items()}

        response_str = f'privmsg logger handlers registered: {response}' if response else 'no privmsg logger handlers registered'
        self.bot.say(response_str)
        self.logger.info(f'plhs given to {sender_nick}: {response}')
