from plugin import *


class bot_remote_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    @admin
    def disconnect(self, sender_nick, **kwargs):
        self.logger.warning('disconnect by %s' % sender_nick)
        self.bot.disconnect('[disconnect]')

    @command
    @admin
    def die(self, sender_nick, **kwargs):
        self.logger.warning('die by %s' % sender_nick)
        self.bot.die('[die]')

    @command
    @admin
    def cycle(self, sender_nick, **kwargs):
        self.logger.warning('cycle by %s' % sender_nick)
        self.bot.send_response_to_channel('operation not supported')

    @command
    @admin
    def reconnect(self, sender_nick, **kwargs):
        self.logger.warning('reconnect by %s' % sender_nick)
        self.bot.connection.reconnect()
