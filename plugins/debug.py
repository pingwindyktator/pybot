from plugin import *


class debug(plugin):
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

    def _generate_markdown_help(self):
        # TODO: WIP
        commands_by_plugin = self.bot.get_commands_by_plugin()
        for plugin_name in commands_by_plugin:
            plugin_instance = self.bot.get_plugin(plugin_name)
            plugin_help = f'\\: {getattr(plugin_instance, "__doc_string")}'.strip() if hasattr(plugin_instance, '__doc_string') else ''
            print(f'#### {plugin_name}{plugin_help}', end='  \n')

            for command_name in commands_by_plugin[plugin_name]:
                command = self.bot.get_commands()[command_name]
                command_helps = getattr(command, '__doc_string').split('\n') if hasattr(command, '__doc_string') else []
                for command_help in command_helps:
                    print(f'* {command_name}\\: {command_help.strip()}', end='  \n')
