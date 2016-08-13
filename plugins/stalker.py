from plugin import *


class stalker(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.database = {}  # map host -> {nickname}
        self.logger = logging.getLogger(__name__)

    def on_pubmsg(self, connection, raw_msg):
        self.bot.whois(raw_msg.source.nick)

    def on_whoisuser(self, connection, raw_msg):
        nick = raw_msg.arguments[0]
        host = raw_msg.arguments[2]
        if host in self.database:
            if nick not in self.database[host]:
                self.database[host].update([nick])
                self.logger.info('new database entry: %s -> %s' % (host, nick))
        else:
            self.database[host] = {nick}
            self.logger.info('new database entry: %s -> %s' % (host, nick))

    @admin
    @command
    def stalk_nick(self, sender_nick, args):
        if not args: return
        nick = args[0]
        result = [host for host in self.database if nick in self.database[host]]
        response = ''
        if result:
            response = 'known hosts of %s: %s ' % (nick, result)
        else:
            response = "I know nothing about %s" % nick
        self.bot.send_response_to_channel(response)
        self.logger.info('%s asks about hosts of %s: %s' % (sender_nick, nick, result))

    @admin
    @command
    def stalk_host(self, sender_nick, args):
        if not args: return
        host = args[0]
        result = self.database[host] if host in self.database else None
        response = ''
        if result:
            response = 'known nicks from %s: %s' % (host, result)
        else:
            response = "I know nothing about %s" % host
        self.bot.send_response_to_channel(response)
        self.logger.info('%s asks about nicks from %s: %s' % (sender_nick, host, result))
