from plugin import *


class echo(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @doc('echo <message>: force bot to say <message>')
    def echo(self, sender_nick, msg, **kwargs):
        self.bot.say(msg)
        self.logger.info(f"echo '{msg}' for {sender_nick}")
