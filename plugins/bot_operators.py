from plugin import *


class bot_operators(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @admin
    @doc('add_op <nickname>: add bot operator')
    def add_op(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if self.bot.is_user_op(nickname):
            self.bot.say(f'{nickname} is already bot operator')
            return

        self.bot.add_op(nickname)
        self.bot.say(f'{nickname} is now bot operator')
        self.logger.warning(f'{sender_nick} added bot operator: {nickname}')

    @command
    @admin
    @doc('rm_op <nickname>: remove bot operator')
    def rm_op(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if not self.bot.is_user_op(nickname):
            self.bot.say(f'{nickname} is not bot operator')
            return

        if nickname == self.bot.config['superop']:
            self.bot.say(f'{nickname} is superop, I cannot remove him')
            return

        self.bot.rm_op(nickname)
        self.bot.say(f'{nickname} is no longer bot operator')
        self.logger.warning(f'{sender_nick} removed bot operator: {nickname}')

    @command
    @admin
    @doc('get bot operators')
    def ops(self, sender_nick, **kwargs):
        ops = self.bot.get_ops()

        if len(ops) == 0:
            self.bot.say('no bot operators')
        else:
            self.bot.say(f'bot operators: {", ".join(ops)}')

        self.logger.info(f'{sender_nick} asked for ops: {ops}')
