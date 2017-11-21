import re

from plugin import *


@doc("correct your previous message, supports regular linux's sed format with g, I flags")
class sed(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.database = {}  # {nickname -> last_msg}
        self.regex = re.compile(r'^s([/|,!])(.+)\1(.*)\1([gI]*)$')

    def on_pubmsg(self, source, msg, **kwargs):
        found = self.regex.findall(msg)
        if found and source.nick in self.database:
            to_replace = found[0][1]
            replace_with = found[0][2]

            flags = found[0][3] if len(found[0]) > 3 else ''
            replace_all = 'g' in flags
            ignore_case = 'I' in flags

            new_msg = re.sub(to_replace, replace_with, self.database[source.nick], 0 if replace_all else 1, re.I if ignore_case else 0)
            if new_msg != self.database[source.nick]:
                self.bot.say(f'{source.nick} meant {repr(new_msg)}')
        else:
            self.database[source.nick] = msg
