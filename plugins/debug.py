from plugin import *


class debug(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    @admin
    def _debug(self, sender_nick, args):
        self.logger.warn('_debug called by %s' % sender_nick)
