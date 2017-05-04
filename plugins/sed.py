import re

from plugin import *


class sed(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.database = {}  # {nickname -> last_msg}
        self.regex = re.compile(r'^s/(.*)/(.*)/(g?)$')

    def on_pubmsg(self, source, msg, **kwargs):
        found = self.regex.findall(msg)
        if self.regex.findall(msg):
            if source.nick not in self.database: return
            to_replace = found[0][0]
            replace_with = found[0][1]
            replace_all = found[0][2]
            new_msg = re.sub(to_replace, replace_with, self.database[source.nick], 0 if replace_all else 1)
            if new_msg != self.database[source.nick]:
                self.bot.say('%s meant %s' % (source.nick, repr(new_msg)))
        else:
            self.database[source.nick] = msg
