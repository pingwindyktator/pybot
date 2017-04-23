import re

from plugin import *


class words_blacklist(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.blacklist = set()
        self.logger = logging.getLogger(__name__)

    def on_pubmsg(self, raw_msg, **kwargs):
        full_msg = raw_msg.arguments[0]
        sender_nick = raw_msg.source.nick

        for word in self.blacklist:
            if re.findall(word, full_msg) and sender_nick not in self.bot.ops:
                self.bot.connection.kick(self.bot.channel, sender_nick, 'watch your language!')
                self.logger.info('%s kicked [%s]' % (sender_nick, word))

    @command
    @admin
    def ban_word(self, sender_nick, args, **kwargs):
        if not args: return
        self.blacklist.update(args)
        self.bot.send_response_to_channel("%s banned" % args)
        self.logger.info("words %s banned by %s" % (args, sender_nick))

    @command
    @admin
    def unban_word(self, sender_nick, args, **kwargs):
        to_unban = [arg for arg in args if arg in self.blacklist]
        if not to_unban: return
        for arg in to_unban:
            self.blacklist.remove(arg)

        self.bot.send_response_to_channel("%s unbanned" % to_unban)
        self.logger.info("words %s unbanned by %s" % (to_unban, sender_nick))
