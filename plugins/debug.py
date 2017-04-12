from plugin import *


class debug(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    @admin
    def _debug(self, sender_nick, **kwargs):
        self.logger.warning('_debug called by %s' % sender_nick)
