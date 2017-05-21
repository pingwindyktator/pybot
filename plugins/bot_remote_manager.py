from plugin import *


class bot_remote_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @admin
    @doc('disconnect from server')
    def disconnect(self, sender_nick, **kwargs):
        self.logger.warning(f'disconnect by {sender_nick}')
        self.bot.disconnect(self.config['disconnect_msg'])

    @command
    @admin
    @doc('kill pybot')
    def die(self, sender_nick, **kwargs):
        self.logger.warning(f'die by {sender_nick}')
        self.bot.die('[die]')

    @command
    @admin
    @doc('cycle the channel')
    def cycle(self, sender_nick, **kwargs):
        self.logger.warning(f'cycle by {sender_nick}')
        self.bot.leave_channel()
        self.bot.join_channel()

    @command
    @admin
    @doc('reconnect to server')
    def reconnect(self, sender_nick, **kwargs):
        self.logger.warning(f'reconnect by {sender_nick}')
        self.bot.connection.reconnect()
