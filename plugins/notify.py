import re

import msg_parser
from plugin import *


class notify(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.database = {}  # map username -> {words to watch}

    def on_pubmsg(self, connection, raw_msg):
        self.find_word(raw_msg.source.nick, raw_msg.arguments[0])

    def find_word(self, sender_nick, msg):
        for register_nickname in self.database:
            for alias in self.database[register_nickname]:
                if alias in re.findall(r"[\w']+", msg) and sender_nick != register_nickname:
                    self.bot.send_response_to_channel(register_nickname)
                    self.logger.info("found alias '%s' for %s" % (alias, register_nickname))
                    break

    @command
    def notify(self, sender_nick, args):
        if len(args) == 0: return

        if sender_nick in self.database:
            self.database[sender_nick].update(args)
        else:
            self.database[sender_nick] = set(args)

        self.bot.send_response_to_channel('notifying for %s' % ', '.join(args))
        self.logger.info('now notifying: %s -> %s' % (args, sender_nick))

    @command
    def rm_notify(self, sender_nick, args):
        if sender_nick not in self.database: return
        to_remove = [arg for arg in args if arg in self.database[sender_nick]]
        if not to_remove: return

        for arg in to_remove:
            self.database[sender_nick].remove(arg)

        self.bot.send_response_to_channel('notifying for %s disabled' % ', '.join(to_remove))
        self.logger.info('stop notifying: %s -> %s' % (to_remove, sender_nick))

    @command
    def notifies(self, sender_nick, args):
        result = self.database[sender_nick] if sender_nick in self.database else {}
        self.bot.send_response_to_channel('notifying %s -> %s' % (result, sender_nick))
        self.logger.info('notifying %s -> %s' % (result, sender_nick))

