from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def help(self, sender_nick, args):
        commands = self.bot.get_commands_by_plugin()
        for p in commands:
            if commands[p]:  # != []
                self.bot.send_response_to_channel('available commands for %s: %s' % (p, ', '.join(commands[p])))

        self.logger.info('help given for %s' % sender_nick)

    @command
    @admin
    def _debug(self, sender_nick, args):
        self.logger.warn('_debug called by %s' % sender_nick)
        self.bot.whois(args[0] if len(args) > 0 else 'pingwindyktator')

    @command
    @admin
    def add_op(self, sender_nick, args):
        if len(args) == 0: return
        self.bot.ops.update(args)
        subreply = 'is now op' if len(args) == 1 else 'are now ops'
        self.bot.send_response_to_channel('%s %s' % (', '.join(args), subreply))
        self.logger.warn('%s added new ops: %s' % (sender_nick, args))

    @command
    @admin
    def rm_op(self, sender_nick, args):
        to_remove = [arg for arg in args if arg in self.bot.ops]
        if not to_remove: return
        for arg in to_remove:
            self.bot.ops.remove(arg)

        subreply = 'is no longer op' if len(to_remove) == 1 else 'are no longer ops'
        self.bot.send_response_to_channel('%s %s' % (', '.join(to_remove), subreply))
        self.logger.warn('%s removed ops: %s' % (sender_nick, to_remove))

    @command
    @admin
    def ops(self, sender_nick, args):
        if len(self.bot.ops) == 0:
            subreply = 'no bot operators'
        elif len(self.bot.ops) == 1:
            subreply = 'bot operator:'
        else:
            subreply = 'bot operators:'

        self.bot.send_response_to_channel('%s %s' % (subreply, ', '.join(self.bot.ops)))
        self.logger.info('%s asked for ops: %s' % (sender_nick, self.bot.ops))
