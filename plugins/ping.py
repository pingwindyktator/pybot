from plugin import *


class ping(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def ping(self, sender_nick, args):
        self.logger.info('pinged by %s' % sender_nick)
        self.bot.send_response_to_channel('pong')
