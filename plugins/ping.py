from plugin import *


class ping(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    def ping(self, sender_nick, **kwargs):
        self.logger.info(f'pinged by {sender_nick}')
        self.bot.say('pong')
        
    @command
    def pong(self, sender_nick, **kwargs):
        self.logger.info(f'ponged by {sender_nick}')
        self.bot.say('ping')
