import time
from threading import Thread, Lock
import json
import sqlite3

from plugin import *


class stalker(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

        self.db_name = 'stalker'
        self.db_connection = sqlite3.connect(self.db_name + '.db', check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute("CREATE TABLE IF NOT EXISTS '%s' (host TEXT primary key not null, nicks TEXT)" % self.db_name)  # host -> {nicknames}
        self.db_mutex = Lock()
        self.get_all_hosts_from_database()
        self.updating_thread = None

    def on_pubmsg(self, connection, raw_msg):
        self.update_database(raw_msg.source.nick, raw_msg.source.host)

    def on_whoisuser(self, connection, raw_msg):
        self.update_database(raw_msg.arguments[0], raw_msg.arguments[2])

    def on_join(self, connection, raw_msg):
        self.update_database(raw_msg.source.nick, raw_msg.source.host)

    def on_me_joined(self, connection, raw_msg):
        if self.updating_thread is None or not self.updating_thread.is_alive():
            self.updating_thread = Thread(target=self.update_all)
            self.updating_thread.start()

    def update_all(self):
        self.logger.info("updating whole stalker's database started...")
        channels = self.bot.channels
        for channel in channels:
            for username in channels[channel].users():
                self.bot.whois(username)
                time.sleep(1)  # to not get kicked because of Excess Flood

        self.logger.info("updating whole stalker's database finished")

    def update_database(self, nick, host):
        result = self.get_nicknames_from_database(host)
        if result is not None:
            if nick not in result:
                result.extend([nick])
                with self.db_mutex:
                    self.db_cursor.execute("UPDATE '%s' SET nicks = ? WHERE host = '%s'" % (self.db_name, host), [json.dumps(result)])
                    self.db_connection.commit()

                self.logger.info('new database entry: %s -> %s' % (host, nick))
        else:
            with self.db_mutex:
                self.db_cursor.execute("INSERT INTO '%s' VALUES (?, ?)" % self.db_name, (host, json.dumps([nick])))
                self.db_connection.commit()

            self.logger.info('new database entry: %s -> %s' % (host, nick))

    def get_nicknames_from_database(self, host):
        with self.db_mutex:
            self.db_cursor.execute("SELECT nicks FROM '%s' WHERE host = '%s'" % (self.db_name, host))
            result = self.db_cursor.fetchone()

        if result is not None:
            result = json.loads(result[0])

        return result

    def get_all_nicknames_from_database(self):
        with self.db_mutex:
            self.db_cursor.execute("SELECT nicks FROM '%s'" % self.db_name)
            result = self.db_cursor.fetchall()

        return [json.loads(x[0]) for x in result]

    def get_all_hosts_from_database(self):
        with self.db_mutex:
            self.db_cursor.execute("SELECT host FROM '%s'" % self.db_name)
            result = self.db_cursor.fetchall()

        return [x[0] for x in result]

    @command
    def stalk_nick(self, sender_nick, args, **kwargs):
        if not args: return
        nick = args[0]
        result = [host for host in self.get_all_hosts_from_database() if nick in self.get_nicknames_from_database(host)]

        if result:
            response = 'known hosts of %s: %s ' % (nick, result)
        else:
            response = "I know nothing about %s" % nick
        self.bot.send_response_to_channel(response)
        self.logger.info('%s asks about hosts of %s: %s' % (sender_nick, nick, result))

    @command
    def stalk(self, sender_nick, args, **kwargs):
        if not args: return
        nick = args[0]
        result = set()
        for x in self.get_all_nicknames_from_database():
            if nick in x: result.update(x)

        if result:
            response = 'other nicks of %s: %s' % (nick, result)
        else:
            response = "I know nothing about %s" % nick
        self.bot.send_response_to_channel(response)
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
        self.bot.send_response_to_channel(response)
        self.logger.info('%s asks about nicks from %s: %s' % (sender_nick, host, nicks))
