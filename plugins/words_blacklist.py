import re

from plugin import *


class words_blacklist(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.blacklist = set()

    def on_pubmsg(self, source, msg, **kwargs):
        for word in self.blacklist:
            if re.findall(word, msg) and source.nick not in self.bot.config['ops']:
                self.bot.connection.kick(self.bot.channel, source.nick, 'watch your language!')
                self.logger.info('%s kicked [%s]' % (source.nick, word))

    @command
    @admin
    def ban_word(self, sender_nick, args, **kwargs):
        if not args: return
        self.blacklist.update(args)
        self.bot.say("%s banned" % args)
        self.logger.info("words %s banned by %s" % (args, sender_nick))

    @command
    @admin
    def unban_word(self, sender_nick, args, **kwargs):
        to_unban = [arg for arg in args if arg in self.blacklist]
        if not to_unban: return
        for arg in to_unban:
            self.blacklist.remove(arg)

        self.bot.say("%s unbanned" % to_unban)
        self.logger.info("words %s unbanned by %s" % (to_unban, sender_nick))
