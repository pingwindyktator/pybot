import re

from plugin import *


class words_blacklist(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.blacklist = set()

    def on_pubmsg(self, source, msg, **kwargs):
        for word in self.blacklist:
            if re.findall(word, msg) and source.nick not in self.bot.config['ops']:
                self.bot.connection.kick(self.bot.config['channel'], source.nick, 'watch your language!')
                self.logger.info(f'{source.nick} kicked [{word}]')

    @command
    @admin
    def ban_word(self, sender_nick, args, **kwargs):
        if not args: return
        self.blacklist.update(args)
        self.bot.say(f"{args} banned")
        self.logger.info(f"words {args} banned by {sender_nick}")

    @command
    @admin
    def unban_word(self, sender_nick, args, **kwargs):
        to_unban = [arg for arg in args if arg in self.blacklist]
        if not to_unban: return
        for arg in to_unban:
            self.blacklist.remove(arg)

        self.bot.say(f"{to_unban} unbanned")
        self.logger.info(f"words {to_unban} unbanned by {sender_nick}")
