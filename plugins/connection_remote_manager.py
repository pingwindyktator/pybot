from plugin import *


class connection_remote_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command(superadmin=True)
    @doc('kill pybot')
    def die(self, sender_nick, **kwargs):
        self.logger.warning(f'die by {sender_nick}')
        self.bot.die('[die]')

    @command(admin=True)
    @doc('cycle the channel')
    def cycle(self, sender_nick, **kwargs):
        self.logger.warning(f'cycle by {sender_nick}')
        self.bot.leave_channel()
        self.bot.join_channel()
