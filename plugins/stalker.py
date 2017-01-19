import time
from threading import Thread

from plugin import *


class stalker(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.database = {}  # map host -> {nickname}
        self.logger = logging.getLogger(__name__)
        self.updating_thread = Thread(target=self.update_all)

    def on_pubmsg(self, connection, raw_msg):
        self.update_database(raw_msg.source.nick, raw_msg.source.host)

    def on_whoisuser(self, connection, raw_msg):
        self.update_database(raw_msg.arguments[0], raw_msg.arguments[2])

    def on_join(self, connection, raw_msg):
        self.update_database(raw_msg.source.nick, raw_msg.source.host)

    def on_me_joined(self, connection, raw_msg):
        self.updating_thread.start()

    def update_all(self):
        self.logger.info("updating whole stalker's database started...")
        for channel in self.bot.channels:
            for username in self.bot.channels[channel].users():
                self.bot.whois(username)
                time.sleep(1)  # to not get kicked because of Excess Flood

        self.logger.info("updating whole stalker's database finished")

    def update_database(self, nick, host):
        if host in self.database:
            if nick not in self.database[host]:
                self.database[host].update([nick])
                self.logger.info('new database entry: %s -> %s' % (host, nick))
        else:
            self.database[host] = {nick}
            self.logger.info('new database entry: %s -> %s' % (host, nick))

    @command
    def stalk_nick(self, sender_nick, args):
        if not args: return
        nick = args[0]
        result = [host for host in self.database if nick in self.database[host]]
        if result:
            response = 'known hosts of %s: %s ' % (nick, result)
        else:
            response = "I know nothing about %s" % nick
        self.bot.send_response_to_channel(response)
        self.logger.info('%s asks about hosts of %s: %s' % (sender_nick, nick, result))

    @command
    def stalk(self, sender_nick, args):
        if not args: return
        nick = args[0]
        result = []
        for x in self.database.values():
            if nick in x: result.extend(x)

        if result:
            response = 'other nicks of %s: %s' % (nick, result)
        else:
            response = "I know nothing about %s" % nick
        self.bot.send_response_to_channel(response)
        self.logger.info('%s stalks %s: %s' % (sender_nick, nick, result))

    @command
    def stalk_host(self, sender_nick, args):
        if not args: return
        nick = args[0]
        hosts = self.database[nick] if nick in self.database else None
        if hosts:
            response = 'known nicks from %s: %s' % (nick, hosts)
        else:
            response = "I know nothing about %s" % nick
        self.bot.send_response_to_channel(response)
        self.logger.info('%s asks about nicks from %s: %s' % (sender_nick, nick, hosts))
