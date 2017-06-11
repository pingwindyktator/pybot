import random

from plugin import *


class echo(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @doc('echo <message>: force bot to say <message>')
    def echo(self, sender_nick, msg, **kwargs):
        self.bot.say(msg)
        self.logger.info(f"echo '{msg}' for {sender_nick}")

    @command
    def thx(self, sender_nick, **kwargs):
        replies = ['spx', 'np', f'np, {sender_nick}', ':)', 'any time', 'de nada', "you're welcome"]
        self.bot.say(random.choice(replies))
        self.logger.info(f"thx from {sender_nick}!")
