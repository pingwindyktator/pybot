import random

from datetime import timedelta
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

    @command
    def thanks(self, **kwargs):
        self.thx(**kwargs)

    @command
    def next(self, **kwargs):
        self.bot.say('another satisfied customer, next please!')

    @command
    def gimmegimmegimme(self, **kwargs):
        self.bot.say('a man after midnight!')

    @command
    def lenny(self, **kwargs):
        self.bot.say('( ͡° ͜ʖ ͡°)')

    @command
    def lifeislife(self, **kwargs):
        self.bot.say('la la la la la!')

    @command(admin=True)
    def server_uptime(self, sender_nick, **kwargs):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(timedelta(seconds=uptime_seconds))

        self.bot.say(uptime_string)

    @command
    @doc('reply "pong"')
    def ping(self, sender_nick, **kwargs):
        self.logger.info(f'pinged by {sender_nick}')
        self.bot.say('pong')

    @command
    @doc('reply "ping"')
    def pong(self, sender_nick, **kwargs):
        self.logger.info(f'ponged by {sender_nick}')
        self.bot.say('ping')
