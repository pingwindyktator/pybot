import re

from datetime import timedelta
from plugin import *


class words_blacklist(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.blacklist = set()  # TODO db

    def on_pubmsg(self, source, msg, **kwargs):
        for word in self.blacklist:
            if re.findall(word, msg) and not self.is_whitelisted(source.nick):
                if self.am_i_channel_operator():
                    self.bot.kick(source.nick, 'watch your language!')
                    self.logger.warning(f'{source.nick} kicked [{word}]')
                else:
                    self.logger.warning(f'{source.nick} cannot be kicked [{word}], operator privileges needed')

    @command(admin=True)
    @doc('ban_word <regex>: ban <regex>. When it appears on chat, bot will kick its sender')
    def ban_word(self, sender_nick, msg, **kwargs):
        if not msg: return
        try:
            _ = re.compile(msg)
        except Exception:
            self.bot.say(f'it does not look like a valid regex pattern')
            return

        suffix = ', but I need operator privileges to kick ;(' if not self.am_i_channel_operator() else ''
        self.blacklist.add(msg)
        self.bot.say(f'"{msg}" banned{suffix}')
        self.logger.info(f'regex "{msg}" banned by {sender_nick}')

    @command(admin=True)
    @doc('unban_word <regex>: unban <regex>')
    def unban_word(self, sender_nick, msg, **kwargs):
        if msg in self.blacklist:
            self.blacklist.remove(msg)

        self.bot.say_ok()
        self.logger.info(f'regex "{msg}" unbanned by {sender_nick}')

    def am_i_channel_operator(self):
        return self.bot.get_channel().is_oper(self.bot.get_nickname())

    @utils.timed_lru_cache(expiration=timedelta(seconds=5), typed=True)
    def is_whitelisted(self, sender_nick):
        if self.bot.is_user_op(sender_nick): return True
        if self.bot.get_channel().is_oper(sender_nick): return True
        if self.bot.get_channel().is_voiced(sender_nick): return True

        return False