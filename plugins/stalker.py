import os
import time
import json
import sqlite3

from threading import Thread, Lock
from plugin import *


@doc('track users to detect multiple nicknames used')
class stalker(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = self.bot.config['server']
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)

        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (host TEXT primary key not null, nicks TEXT)")  # host -> {nicknames}
        self.db_mutex = Lock()
        self.updating_thread = None

    def on_welcome(self, **kwargs):
        self.bot.names()

    def on_pubmsg(self, source, **kwargs):
        self.update_database(source.nick, source.host)

    def on_ctcp(self, source, **kwargs):
        self.update_database(source.nick, source.host)

    def on_whoisuser(self, nick, host, **kwargs):
        self.update_database(nick, host)

    def on_join(self, source, **kwargs):
        self.update_database(source.nick, source.host)

    def on_nick(self, source, new_nickname, **kwargs):
        self.update_database(new_nickname, source.host)

    def on_namreply(self, nicknames, **kwargs):
        if self.updating_thread is None or not self.updating_thread.is_alive():
            self.updating_thread = Thread(target=self.update_all, args=(nicknames,))
            self.updating_thread.start()

    def update_all(self, nicknames):
        self.logger.info("updating whole stalker's database started...")
        for nick in nicknames:
            self.bot.whois(nick)
            time.sleep(1)  # to not get kicked because of Excess Flood

        self.logger.info("updating whole stalker's database finished")

    def update_database(self, nick, host):
        result = self.get_nicknames_from_database(host)
        if result:
            if nick not in result:
                result.extend([nick])
                with self.db_mutex:
                    self.db_cursor.execute(f"UPDATE '{self.db_name}' SET nicks = ? WHERE host = ?", (json.dumps(result), host))
                    self.db_connection.commit()

                self.logger.info(f'new database entry: {host} -> {nick}')
        else:
            with self.db_mutex:
                self.db_cursor.execute(f"INSERT INTO '{self.db_name}' VALUES (?, ?)", (host, json.dumps([nick])))
                self.db_connection.commit()

            self.logger.info(f'new database entry: {host} -> {nick}')

    def get_nicknames_from_database(self, host):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT nicks FROM '{self.db_name}' WHERE host = ?", (host,))
            result = self.db_cursor.fetchone()

        if result:
            result = json.loads(result[0])
            result = [irc_nickname(x) for x in result]

        return result

    def get_all_nicknames_from_database(self):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT nicks FROM '{self.db_name}'")
            result = self.db_cursor.fetchall()

        if result:
            result = [json.loads(x[0]) for x in result]
            result = [[irc_nickname(y) for y in x] for x in result]

        return result

    def get_all_hosts_from_database(self):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT host FROM '{self.db_name}'")
            result = self.db_cursor.fetchall()

        if result:
            result = [x[0] for x in result]

        return result

    @command
    @doc('stalk_nick <nickname>: get all known hosts of <nickname> user')
    def stalk_nick(self, sender_nick, args, **kwargs):
        if not args: return
        nick = irc_nickname(args[0])
        all_hosts = self.get_all_hosts_from_database()
        result = set([host for host in all_hosts if nick in self.get_nicknames_from_database(host)])

        if result:
            response = f'known hosts of {nick}: {result} '
        else:
            response = f'I know nothing about {nick}'

        self.bot.say(response)
        self.logger.info(f'{sender_nick} asks about hosts of {nick}: {result}')

    @command
    @doc("stalk <nickname>: get other <nickname> user's nicknames")
    def stalk(self, sender_nick, args, **kwargs):
        if not args: return
        nick = irc_nickname(args[0])
        result = set()
        all_nicknames = self.get_all_nicknames_from_database()
        for x in all_nicknames:
            if nick in x: result.update(x)

        if result:
            response = f'other nicks of {nick}: {result}'
        else:
            response = f"I know nothing about {nick}"
        self.bot.say(response)
        self.logger.info(f'{sender_nick} stalks {nick}: {result}')

    @command
    @doc('stalk_host <host>: get all nicknames from <host>')
    def stalk_host(self, sender_nick, args, **kwargs):
        if not args: return
        host = args[0]
        nicks = self.get_nicknames_from_database(host)
        if nicks:
            response = f'known nicks from {host}: {nicks}'
        else:
            response = f"I know nothing about {host}"
        self.bot.say(response)
        self.logger.info(f'{sender_nick} asks about nicks from {host}: {nicks}')
