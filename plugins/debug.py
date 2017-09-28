from plugin import *


class debug(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @admin
    @doc('for debug purposed only, use during development to trigger needed actions')
    def _debug(self, sender_nick, **kwargs):
        self.logger.warning(f'_debug called by {sender_nick}')
