from plugin import *


class stats(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @admin
    @command
    def stats(self, sender_nick, **kwargs):
        items = self.bot.channels.items()
        for chname, chobj in items:
            self.bot.say("--- Channel statistics ---")
            self.bot.say("Channel: " + chname)
            users = sorted(chobj.users())
            self.bot.say("Users: " + ", ".join(users))
            opers = sorted(chobj.opers())
            self.bot.say("Opers: " + ", ".join(opers))
            voiced = sorted(chobj.voiced())
            self.bot.say("Voiced: " + ", ".join(voiced))

            self.logger.info('channel stats given to %s' % sender_nick)
