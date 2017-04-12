from plugin import *


class stats(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @admin
    @command
    def stats(self, sender_nick, **kwargs):
        for chname, chobj in self.bot.channels.items():
            self.bot.send_response_to_channel("--- Channel statistics ---")
            self.bot.send_response_to_channel("Channel: " + chname)
            users = sorted(chobj.users())
            self.bot.send_response_to_channel("Users: " + ", ".join(users))
            opers = sorted(chobj.opers())
            self.bot.send_response_to_channel("Opers: " + ", ".join(opers))
            voiced = sorted(chobj.voiced())
            self.bot.send_response_to_channel("Voiced: " + ", ".join(voiced))

            self.logger.info('channel stats given to %s' % sender_nick)
