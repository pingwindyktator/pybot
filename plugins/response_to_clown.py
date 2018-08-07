from plugin import *


class response_to_clown(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.kick_counter = 3
        self.clown = 'daniel1302'
        self.annoying_tab = ['jak życie', 'jakżycie', 'jak zycie', 'jakzycie']

    def on_pubmsg(self, source, msg, **kwargs):
        if source.nick == self.clown and 'riemann' in msg:
            for possible_annoying in self.annoying_tab:
                if possible_annoying in msg:
                    if self.kick_counter:
                        self.bot.say("{}!".format(self.kick_counter))
                        self.kick_counter -= 1
                    else:
                        self.kick_counter = 3
                        self.bot.kick(source.nick, 'You are so boring..')

