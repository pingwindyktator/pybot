from plugin import *


class echo(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def echo(self, sender_nick, msg, **kwargs):
        self.bot.say(msg)
        self.logger.info("echo '%s' for %s" % (msg, sender_nick))
