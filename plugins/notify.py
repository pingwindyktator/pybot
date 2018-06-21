import re

from plugin import *


class notify(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.database = {}  # username -> {words to watch}
        # TODO db

    def on_pubmsg(self, source, msg, **kwargs):
        if self.bot.is_user_ignored(source.nick): return
        self.find_word(source.nick, msg)

    def find_word(self, sender_nick, full_msg):
        for register_nickname in self.database:
            for alias in self.database[register_nickname]:
                if re.findall(alias.casefold(), full_msg) and sender_nick != register_nickname:
                    self.bot.say(register_nickname)
                    self.logger.info(f"found notify set for '{register_nickname}': {alias}")
                    break

    @command
    @doc("notify <args>...: set notify for <args>. bot will call your nickname when one of <args> appears on chat. supports regular expressions")
    def notify(self, sender_nick, args, **kwargs):
        if len(args) == 0: return

        if sender_nick in self.database:
            self.database[sender_nick].update(args)
        else:
            self.database[sender_nick] = set(args)

        self.bot.say(f'notifying for {args}')
        self.logger.info(f'now notifying: {args} -> {sender_nick}')

    @command
    @doc('rm_notify <args>...: remove notify for <args>')
    def rm_notify(self, sender_nick, args, **kwargs):
        if sender_nick not in self.database: return
        to_remove = [arg for arg in args if arg in self.database[sender_nick]]
        if not to_remove: return

        for arg in to_remove: self.database[sender_nick].remove(arg)

        self.bot.say(f'no longer notifying for {to_remove}')
        self.logger.info(f'stop notifying: {to_remove} -> {sender_nick}')

    @command
    @doc("get your notifies saved")
    def notifies(self, sender_nick, **kwargs):
        result = self.database[sender_nick] if sender_nick in self.database else {}
        if result:
            self.bot.say(f'notifying {result} -> {sender_nick}')
        else:
            self.bot.say(f'no notifies set for {sender_nick}')

        self.logger.info(f'notifying {result} -> {sender_nick}')

