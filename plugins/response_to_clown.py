import re

from plugin import *


class response_to_clown(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.kick_counter = 3
        self.clown = irc_nickname('daniel1302')
        self.riemann = irc_nickname('riemann')
        self.annoying_msg = re.compile('jak.*?ycie', re.IGNORECASE)

    def is_same_nickname(self, a, b):
        strip_str = ' _' + string.digits
        a = a.casefold().strip(strip_str)
        b = b.casefold().strip(strip_str)
        return a == b and a

    def on_pubmsg(self, source, msg, **kwargs):
        if self.riemann in msg                               \
          and self.is_same_nickname(source.nick, self.clown) \
          and annoying_msg.match(msg):
            if self.kick_counter:
                self.bot.say(f'{self.kick_counter}!')
                self.kick_counter -= 1
            else:
                self.kick_counter = 3
                self.bot.kick(self.clown, 'You are so boring..')
                self.logger.warning(f'{self.clown} kicked')

