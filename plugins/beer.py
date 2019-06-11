import json
import os
import sqlite3

from contextlib import suppress
from threading import RLock
from plugin import *


class beer(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_mutex = RLock()

    @command
    @doc('beer <nickname> <reason>: give <nickname> a beer because of <reason>')
    def beer(self, sender_nick, args, msg, **kwargs):
        if not msg: return
        nickname = irc_nickname(args[0])
        reason = msg[len(nickname):].strip()

        if nickname == sender_nick:
            self.bot.say('orly?')
            return

        if nickname == self.bot.get_nickname():
            self.bot.say('thank you!')
            return

        self.logger.info(f'{sender_nick} gives {nickname} beer ({reason})')
        self.add_beer(sender_nick, nickname, reason)
        self.bot.say(self.get_beers_str(sender_nick, nickname))

    @command
    @doc('beer_drank <nickname>: use when you drank a beer put by <nickname>')
    def beer_drank(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if nickname == sender_nick or nickname == self.bot.get_nickname():
            self.bot.say('orly?')
            return

        self.logger.info(f"{sender_nick} drank {nickname}'s beer")
        self.remove_beer(nickname, sender_nick)
        self.bot.say(self.get_beers_str(sender_nick, nickname))

    @command
    @command_alias('beers_get')
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
        if not args: return
        nickname = irc_nickname(args[0])

        if nickname == sender_nick or nickname == self.bot.get_nickname():
            self.bot.say('orly?')
            return

        old = self.get_beers_simple(sender_nick, nickname)
        self.logger.info(f'{sender_nick} resets {nickname} beers, was {old}')
        self.reset(sender_nick, nickname)
        self.bot.say(f'{self.get_beers_simple(sender_nick, nickname)}, was {old}')

    def get_beers_str(self, who, to_whom):
        reasons = self.get_reasons_str(who, to_whom)
        reasons2 = self.get_reasons_str(to_whom, who)
        if not reasons and not self.get_reasons_str(to_whom, who): return self.get_beers_simple(who, to_whom)
        return f'{who} owes {to_whom} {self.get_beers(who, to_whom)} beers {reasons}' + '\n' + \
               f'{to_whom} owes {who} {self.get_beers(to_whom, who)} beers {reasons2}'

    def get_beers_simple(self, who, to_whom):
        return f'{who} {self.get_beers(to_whom, who)}:{self.get_beers(who, to_whom)} {to_whom}'

    def get_beers(self, who, to_whom):
        with self.db_mutex:
            try:
                self.db_cursor.execute(f"SELECT beers FROM '{who.casefold()}' WHERE nickname = ?", (to_whom.casefold(),))
                result = self.db_cursor.fetchone()
            except sqlite3.OperationalError as e:
                return 0

            return result[0] if result else 0

    def reset(self, a, b):
        with self.db_mutex:
            with suppress(sqlite3.OperationalError): self.db_cursor.execute(f"INSERT OR REPLACE INTO '{a.casefold()}' VALUES (?, ?, ?)", (b.casefold(), 0, json.dumps([])))
            with suppress(sqlite3.OperationalError): self.db_cursor.execute(f"INSERT OR REPLACE INTO '{b.casefold()}' VALUES (?, ?, ?)", (a.casefold(), 0, json.dumps([])))
            self.db_connection.commit()

    def get_reasons(self, who, to_whom):
        with self.db_mutex:
            try:
                self.db_cursor.execute(f"SELECT reasons FROM {who.casefold()} WHERE nickname = ?", (to_whom.casefold(), ))
                result = self.db_cursor.fetchall()
            except sqlite3.OperationalError:
                    return []

            return json.loads(result[0][0]) if result and result[0] and result[0][0] else []

    def get_reasons_str(self, who, to_whom):
        reasons = self.get_reasons(who, to_whom)
        return f'({", ".join(reasons)})' if reasons else ''

    def add_beer(self, who, to_whom, reason):
        with self.db_mutex:
            reasons = self.get_reasons(who, to_whom)
            reasons.append(reason)
            beers = self.get_beers(who, to_whom) + 1

            # nickname -> beers, reasons
            self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{who.casefold()}' (nickname TEXT primary key not null, beers INTEGER)")
            with suppress(sqlite3.OperationalError): self.db_cursor.execute(f"ALTER TABLE '{who.casefold()}' ADD COLUMN reasons TEXT")
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{who.casefold()}' VALUES (?, ?, ?)",
                                   (to_whom.casefold(), beers, json.dumps(reasons)))

            self.db_connection.commit()

    def remove_beer(self, who, to_whom):
        with self.db_mutex:
            reasons = self.get_reasons(who, to_whom)
            with suppress(IndexError): reasons.pop(0)
            beers = max(self.get_beers(who, to_whom) - 1, 0)

            # nickname -> beers, reasons
            self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{who.casefold()}' (nickname TEXT primary key not null, beers INTEGER)")
            with suppress(sqlite3.OperationalError): self.db_cursor.execute(f"ALTER TABLE '{who.casefold()}' ADD COLUMN reasons TEXT")
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{who.casefold()}' VALUES (?, ?, ?)",
                                   (to_whom.casefold(), beers, json.dumps(reasons)))

            self.db_connection.commit()
