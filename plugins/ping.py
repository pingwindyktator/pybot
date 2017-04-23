from plugin import *


class ping(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def ping(self, sender_nick, **kwargs):
        self.logger.info('pinged by %s' % sender_nick)
        self.bot.say('pong')
        
    @command
    def pong(self, sender_nick, **kwargs):
        self.logger.info('ponged by %s' % sender_nick)
        self.bot.say('ping')
