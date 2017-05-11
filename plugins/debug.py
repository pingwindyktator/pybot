from plugin import *


class debug(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @admin
    def _debug(self, sender_nick, **kwargs):
        self.logger.warning(f'_debug called by {sender_nick}')
