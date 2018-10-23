from plugin import *


class debug(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command(admin=True)
    @doc('for debug purposed only, use during development to trigger needed actions')
    def _debug(self, sender_nick, **kwargs):
        self.logger.warning(f'_debug called by {sender_nick}')
        # self.bot.say(color.white('white'))
        # self.bot.say(color.black('black'))
        # self.bot.say(color.blue('blue'))
        # self.bot.say(color.green('green'))
        # self.bot.say(color.light_red('light_red'))
        # self.bot.say(color.red('red'))
        # self.bot.say(color.purple('purple'))
        # self.bot.say(color.orange('orange'))
        # self.bot.say(color.yellow('yellow'))
        # self.bot.say(color.light_green('light_green'))
        # self.bot.say(color.cyan('cyan'))
        # self.bot.say(color.light_cyan('light_cyan'))
        # self.bot.say(color.light_blue('light_blue'))
        # self.bot.say(color.pink('pink'))
        # self.bot.say(color.gray('gray'))
        # self.bot.say(color.light_grey('light_grey'))
