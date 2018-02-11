import re
from collections import deque

from plugin import *


@doc("correct your previous message, supports regular linux's sed format with g, I flags")
class sed(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.database = {}  # {nickname -> [last_msgs]}
        self.regex = re.compile(r'^s([/|,!])(.+)\1(.*)\1([gI]*)$')

    def on_pubmsg(self, source, msg, **kwargs):
        if source.nick not in self.database:
            self.database[source.nick] = deque(maxlen=3)
            self.database[source.nick].append(msg)
            return

        found = self.regex.findall(msg)
        if found:
            to_replace = found[0][1]
            replace_with = found[0][2]

            flags = found[0][3] if len(found[0]) > 3 else ''
            replace_all = 'g' in flags
            ignore_case = 'I' in flags

            for old_msg in list(reversed(self.database[source.nick])):
                new_msg = re.sub(to_replace, replace_with, old_msg, 0 if replace_all else 1, re.I if ignore_case else 0)
                if new_msg != old_msg:
                    self.bot.say(f'{source.nick} meant {repr(new_msg)}')
                    break
        else:
            self.database[source.nick].append(msg)
