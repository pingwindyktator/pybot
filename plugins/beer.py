import os
import sqlite3

from contextlib import suppress
from threading import Lock
from plugin import *

# TODO beer_get_all <nickname> should return all beers
# TODO beer_get_all
class beer(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_mutex = Lock()

    @command
    @doc('beer <nickname>: give <nickname> a beer')
    def beer(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if nickname == sender_nick:
            self.bot.say('orly?')
            return

        if nickname == self.bot.get_nickname():
            self.bot.say('thank you!')
            return

        self.logger.info(f'{sender_nick} gives {nickname} beer')
        self.add_beer(sender_nick, nickname)
        self.bot.say(self.get_beers_str(sender_nick, nickname))

    @command
    @doc('beer_rm <nickname>: take <nickname> a beer')
    def beer_rm(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if nickname == sender_nick:
            self.bot.say('orly?')
            return

        if nickname == self.bot.get_nickname():
            self.bot.say(':(')
            return

        self.logger.info(f'{sender_nick} removes {nickname} beer')
        self.remove_beer(sender_nick, nickname)
        self.bot.say(self.get_beers_str(sender_nick, nickname))

    @command
    @doc('beer_get <nickname>: get beers owned <nickname>')
    def beer_get(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if nickname == sender_nick or nickname == self.bot.get_nickname():
            self.bot.say('orly?')
            return

        self.bot.say(self.get_beers_str(sender_nick, nickname))

    @command
    @doc('beer_reset <nickname>: reset owned beers')
    def beer_reset(self, sender_nick, args, **kwargs):
        # TODO authorization
        if not args: return
        nickname = irc_nickname(args[0])

        if nickname == sender_nick or nickname == self.bot.get_nickname():
            self.bot.say('orly?')
            return

        self.logger.info(f'{sender_nick} resets {nickname} beers, was {self.get_beers_str(sender_nick, nickname)}')
        old = self.get_beers_str(sender_nick, nickname)
        self.reset(sender_nick, nickname)
        self.bot.say(f'{self.get_beers_str(sender_nick, nickname)}, was {old}')

    def get_beers_str(self, who, to_whom):
        return f'{who} {self.get_beers(to_whom, who)}:{self.get_beers(who, to_whom)} {to_whom}'

    def get_beers(self, who, to_whom):
        with self.db_mutex:
            try:
                self.db_cursor.execute(f"SELECT beers FROM '{who.casefold()}' WHERE nickname = ?", (to_whom.casefold(),))
                result = self.db_cursor.fetchone()
            except sqlite3.OperationalError:
                return 0

            return result[0] if result else 0

    def reset(self, a, b):
        with self.db_mutex:
            with suppress(sqlite3.OperationalError): self.db_cursor.execute(f"INSERT OR REPLACE INTO '{a.casefold()}' VALUES (?, ?)", (b.casefold(), 0))
            with suppress(sqlite3.OperationalError): self.db_cursor.execute(f"INSERT OR REPLACE INTO '{b.casefold()}' VALUES (?, ?)", (a.casefold(), 0))
            self.db_connection.commit()

    def add_beer(self, who, to_whom):
        with self.db_mutex:
            self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{who.casefold()}' (nickname TEXT primary key not null, beers INTEGER)")  # nickname -> beers
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{who.casefold()}' VALUES (?, COALESCE((SELECT beers + 1 FROM '{who.casefold()}' WHERE nickname = ?), 1))", (to_whom.casefold(), to_whom.casefold()))
            self.db_connection.commit()

    def remove_beer(self, who, to_whom):
        with self.db_mutex:
            self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{who.casefold()}' (nickname TEXT primary key not null, beers INTEGER)")  # nickname -> beers
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{who.casefold()}' VALUES (?, COALESCE((SELECT MAX(beers - 1, 0) FROM '{who.casefold()}' WHERE nickname = ?), 0))", (to_whom.casefold(), to_whom.casefold()))
            self.db_connection.commit()
