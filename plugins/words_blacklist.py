from plugin import *


class words_blacklist(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.blacklist = set()
        self.logger = logging.getLogger(__name__)

    def on_pubmsg(self, connection, raw_msg):
        full_msg = raw_msg.arguments[0]
        sender_nick = raw_msg.source.nick

        for word in self.blacklist:
            if word in full_msg and sender_nick not in self.bot.ops:
                connection.kick(self.bot.channel, sender_nick, 'watch your language!')
                self.logger.info('%s kicked [%s]' % (sender_nick, word))

    @command
    @admin
    def ban_word(self, sender_nick, args):
        if not args: return
        self.blacklist.update(args)
        self.bot.send_response_to_channel("%s banned" % ', '.join(args))
        self.logger.info("words %s banned by %s" % (args, sender_nick))

    @command
    @admin
    def unban_word(self, sender_nick, args):
        to_unban = [arg for arg in args if arg in self.blacklist]
        if not to_unban: return
        for arg in to_unban:
            self.blacklist.remove(arg)

        self.bot.send_response_to_channel("%s unbanned" % ', '.join(to_unban))
        self.logger.info("words %s unbanned by %s" % (to_unban, sender_nick))
