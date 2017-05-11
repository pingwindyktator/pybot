import os
import time
import json
import sqlite3

from threading import Thread, Lock
from plugin import *


class stalker(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = 'stalker'
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)

        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute("CREATE TABLE IF NOT EXISTS '%s' (host TEXT primary key not null, nicks TEXT)" % self.db_name)  # host -> {nicknames}
        self.db_mutex = Lock()
        self.updating_thread = None

    def on_pubmsg(self, source, **kwargs):
        self.update_database(source.nick, source.host)

    def on_whoisuser(self, nick, host, **kwargs):
        self.update_database(nick, host)

    def on_join(self, source, **kwargs):
        self.update_database(source.nick, source.host)

    def on_me_joined(self, **kwargs):
        if self.updating_thread is None or not self.updating_thread.is_alive():
            self.updating_thread = Thread(target=self.update_all)
            self.updating_thread.start()

    def update_all(self):
        self.logger.info("updating whole stalker's database started...")
        users = list(self.bot.channel.users())
        for username in users:
            self.bot.whois(username)
            time.sleep(1)  # to not get kicked because of Excess Flood

        self.logger.info("updating whole stalker's database finished")

    def update_database(self, nick, host):
        nick = nick.lower()
        result = self.get_nicknames_from_database(host)
        if result:
            if nick not in result:
                result.extend([nick])
                with self.db_mutex:
                    self.db_cursor.execute("UPDATE '%s' SET nicks = ? WHERE host = ?" % self.db_name, (json.dumps(result), host))
                    self.db_connection.commit()

                self.logger.info('new database entry: %s -> %s' % (host, nick))
        else:
            with self.db_mutex:
                self.db_cursor.execute("INSERT INTO '%s' VALUES (?, ?)" % self.db_name, (host, json.dumps([nick])))
                self.db_connection.commit()

            self.logger.info('new database entry: %s -> %s' % (host, nick))

    def get_nicknames_from_database(self, host):
        with self.db_mutex:
            self.db_cursor.execute("SELECT nicks FROM '%s' WHERE host = ?" % self.db_name, (host,))
            result = self.db_cursor.fetchone()

        if result:
            result = json.loads(result[0])
            result = [x.lower() for x in result]

        return result

    def get_all_nicknames_from_database(self):
        with self.db_mutex:
            self.db_cursor.execute("SELECT nicks FROM '%s'" % self.db_name)
            result = self.db_cursor.fetchall()

        if result:
            result = [json.loads(x[0]) for x in result]
            result = [[y.lower() for y in x] for x in result]

        return result

    def get_all_hosts_from_database(self):
        with self.db_mutex:
            self.db_cursor.execute("SELECT host FROM '%s'" % self.db_name)
            result = self.db_cursor.fetchall()

        if result:
            result = [x[0] for x in result]

        return result

    @command
    def stalk_nick(self, sender_nick, args, **kwargs):
        if not args: return
        nick = args[0]
        all_hosts = self.get_all_hosts_from_database()
        result = set([host for host in all_hosts if nick.lower() in self.get_nicknames_from_database(host)])

        if result:
            response = 'known hosts of %s: %s ' % (nick, result)
        else:
            response = "I know nothing about %s" % nick

        self.bot.say(response)
        self.logger.info('%s asks about hosts of %s: %s' % (sender_nick, nick, result))

    @command
    def stalk(self, sender_nick, args, **kwargs):
        if not args: return
        nick = args[0]
        result = set()
        all_nicknames = self.get_all_nicknames_from_database()
        for x in all_nicknames:
            if nick.lower() in x: result.update(x)

        if result:
            response = 'other nicks of %s: %s' % (nick, result)
        else:
            response = "I know nothing about %s" % nick
        self.bot.say(response)
        self.logger.info('%s stalks %s: %s' % (sender_nick, nick, result))

    @command
    def stalk_host(self, sender_nick, args, **kwargs):
        if not args: return
        host = args[0]
        nicks = self.get_nicknames_from_database(host)
        if nicks:
            response = 'known nicks from %s: %s' % (host, nicks)
        else:
            response = "I know nothing about %s" % host
        self.bot.say(response)
        self.logger.info('%s asks about nicks from %s: %s' % (sender_nick, host, nicks))
