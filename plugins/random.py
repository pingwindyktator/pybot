import requests
import uuid

from math import floor
from plugin import *


class random(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.random_org_uri = r'https://www.random.org/integers/?num=1&col=1&min=%s&max=%s&base=%s&format=plain&rnd=new'
        self.random_org_str_uri = r'https://www.random.org/strings/?num=%s&len=%s&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain&rnd=new'

    def random_impl(self, args, base, sender_nick):
        if not args:
            _min = 0
            _max = 1000000000  # max defined in random.org API docs
        elif len(args) == 2:
            _min = args[0]
            _max = args[1]
        else: return None, 'Error: not enough arguments'

        self.logger.info(f'getting [{_min}, {_max}) random of base {base} for {sender_nick}')
        result = requests.get(self.random_org_uri % (_min, _max, base)).content.decode().replace('\n', '')
        if result.startswith('Error: '): return None, result
        return result, None

    @command
    @command_alias('random_string')
    @doc("""randoms <length>: fetch random string of length <length> from random.org
            fetch random string of length 100 from random.org""")
    def randoms(self, sender_nick, args, **kwargs):
        if not args:
            _len = 100
        elif len(args) == 1:
            try: _len = int(args[0])
            except ValueError:
                self.bot.say('Error: The length must be an integer in the [1,480] interval')
                return
        else: return

        if _len <= 0 or _len > 480:  # to fit in single IRC msg
            self.bot.say('Error: The length must be an integer in the [1,480] interval')
            return

        a = floor(_len / 20)
        b = _len - (a * 20)
        self.logger.info(f'getting random string of length {_len} for {sender_nick}')
        result = ''
        if a > 0:
            result += requests.get(self.random_org_str_uri % (a, 20)).content.decode().replace('\n', '')
        if b > 0:
            result += requests.get(self.random_org_str_uri % (1, b)).content.decode().replace('\n', '')

        assert len(result) == _len
        assert result

        self.bot.say(result)

    @doc("""random10 <min> <max>: fetch random number in [min, max] from random.org
            fetch random number in [0, 1000000000] from random.org""")
    @command
    @command_alias('random')
    def random10(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 10, sender_nick)
        if result: self.bot.say(result)
        else: self.bot.say(error)

    @doc("""random2 <min> <max>: fetch binary random number in [min, max] from random.org
            fetch binary random number in [0, 1000000000] from random.org""")
    @command
    @command_alias('random_bin')
    def random2(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 2, sender_nick)
        if result: self.bot.say(f'0b{result}')
        else: self.bot.say(error)

    @doc("""random8 <min> <max>: fetch oct random number in [min, max] from random.org
            fetch oct random number in [0, 1000000000] from random.org""")
    @command
    @command_alias('random_oct')
    def random8(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 8, sender_nick)
        if result: self.bot.say(f'0o{result}')
        else: self.bot.say(error)

    @doc("""random16 <min> <max>: fetch hex random number in [min, max] from random.org
            fetch hex random number in [0, 1000000000] from random.org""")
    @command
    @command_alias('random_hex')
    def random16(self, args, sender_nick, **kwargs):
        result, error = self.random_impl(args, 16, sender_nick)
        if result: self.bot.say(f'0x{result}')
        else: self.bot.say(error)

    @doc('generates random uuid1')
    @command
    def uuid1(self, sender_nick, **kwargs):
        self.logger.info(f'generating uuid1 for {sender_nick}')
        self.bot.say(uuid.uuid1())

    @doc('generates random uuid4')
    @command
    @command_alias('uuid')
    def uuid4(self, sender_nick, **kwargs):
        self.logger.info(f'generating uuid4 for {sender_nick}')
        self.bot.say(uuid.uuid4())
