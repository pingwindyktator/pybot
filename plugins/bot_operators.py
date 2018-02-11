from plugin import *


class bot_operators(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @admin
    @doc('add_op <nickname>...: add bot operator')
    def add_op(self, sender_nick, args, **kwargs):
        to_add = [irc_nickname(arg) for arg in args if not self.bot.is_user_op(arg)]
        if not to_add:
            self.bot.say('no one to add')
            return

        for arg in to_add: self.bot.add_op(arg)

        reply = f'{to_add[0]} is now op' if len(to_add) == 1 else f'{to_add} are now ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} added new ops: {to_add}')

    @command
    @admin
    @doc('rm_op <nickname>...: remove bot operator')
    def rm_op(self, sender_nick, args, **kwargs):
        to_remove = [irc_nickname(arg) for arg in args if self.bot.is_user_op(arg)]
        if self.bot.config['superop'] in to_remove:
            to_remove.remove(self.bot.config['superop'])
            self.bot.say(f'{self.bot.config["superop"]} is superop, I cannot remove him')

        if not to_remove:
            self.bot.say('no one to remove')
            return

        for arg in to_remove: self.bot.rm_op(arg)

        reply = f'{to_remove[0]} is no longer op' if len(to_remove) == 1 else f'{to_remove} are no longer ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} removed ops: {to_remove}')

    @command
    @admin
    @doc('get bot operators')
    def ops(self, sender_nick, **kwargs):
        ops = self.bot.get_ops()

        if len(ops) == 0:
            reply = 'no bot operators'
        else:
            reply = f'bot operators: {", ".join(ops)}'

        self.bot.say(reply)
        self.logger.info(f'{sender_nick} asked for ops: {ops}')
