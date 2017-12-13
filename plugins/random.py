import requests
import uuid

from plugin import *


class random(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.random_org_uri = r'https://www.random.org/integers/?num=1&col=1&min=%s&max=%s&base=%s&format=plain&rnd=new'

    def random_impl(self, args, base, sender_nick):
        if not args:
            min = 0
            max = 1000000000  # max defined in random.org API docs
        elif len(args) == 2:
            min = args[0]
            max = args[1]
        else: return None, 'Error: not enough arguments'

        self.logger.info(f'getting [{min}, {max}) random of base {base} for {sender_nick}')
        result = requests.get(self.random_org_uri % (min, max, base)).content.decode('utf-8').replace('\n', '')
        if result.startswith('Error: '): return None, result
        return result, None

    @doc("""random <min> <max>: fetch random number in [min, max) from random.org
            random: fetch random number in [0, 1000000000) from random.org""")
    @command
    def random(self, **kwargs):
        return self.random10(**kwargs)

    @doc("""random10 <min> <max>: fetch random number in [min, max) from random.org
            random10: fetch random number in [0, 1000000000) from random.org""")
    @command
    def random10(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 10, sender_nick)
        if result: self.bot.say(result)
        else: self.bot.say(error)

    @doc("""random2 <min> <max>: fetch binary random number in [min, max) from random.org
            random2: fetch binary random number in [0, 1000000000) from random.org""")
    @command
    def random2(self, args, sender_nick,  **kwargs):
        result, error = self.random_impl(args, 2, sender_nick)
        if result: self.bot.say(f'0b{result}')
        else: self.bot.say(error)

    @doc("""random8 <min> <max>: fetch oct random number in [min, max) from random.org
            random8: fetch oct random number in [0, 1000000000) from random.org""")
    @command
    def random8(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 8, sender_nick)
        if result: self.bot.say(f'0o{result}')
        else: self.bot.say(error)

    @doc("""random16 <min> <max>: fetch hex random number in [min, max) from random.org
            random16: fetch hex random number in [0, 1000000000) from random.org""")
    @command
    def random16(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 16, sender_nick)
        if result: self.bot.say(f'0x{result}')
        else: self.bot.say(error)

    @doc('generates random uuid4')
    @command
    def uuid(self, **kwargs):
        return self.uuid4(**kwargs)

    @doc('generates random uuid1')
    @command
    def uuid1(self, sender_nick, **kwargs):
        self.logger.info(f'generating uuid1 for {sender_nick}')
        self.bot.say(uuid.uuid1())

    @doc('generates random uuid4')
    @command
    def uuid4(self, sender_nick, **kwargs):
        self.logger.info(f'generating uuid4 for {sender_nick}')
        self.bot.say(uuid.uuid4())
