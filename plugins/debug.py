from plugin import *


@doc('for debug purposes only')
class debug(plugin):
    @command(admin=True)
    def _debug(self, sender_nick, **kwargs):
        self.logger.warning(f'_debug called by {sender_nick}')
        self._generate_markdown_help()

    def _generate_markdown_help(self):
        # all plugins should be enabled and loaded

        commands_by_plugin = self.bot.get_commands_by_plugin()
        for plugin_name in sorted(commands_by_plugin.keys()):
            plugin_instance = self.bot.get_plugin(plugin_name)
            plugin_helps = getattr(plugin_instance, '__pybot_docs', [])
            plugin_help = f'\\: {plugin_helps[0].doc_str}' if plugin_helps else ''
            print(f'#### {plugin_name}{plugin_help}', end='  \n')

            for command_name in commands_by_plugin[plugin_name]:
                command = self.bot.get_commands()[command_name]
                command_helps = getattr(command, '__pybot_docs', [])
                if not command_helps:
                    print(f'* {command_name}', end='  \n')

                for command_help in command_helps:
                    command_doc_args = command_help.doc_args
                    command_doc_args = ' '.join([f'<{x}>' for x in command_doc_args])
                    command_doc_args = f' {command_doc_args}' if command_doc_args else ''
                    command_doc_string = command_help.doc_str
                    print(f'* {command_name}{command_doc_args}\\: {command_doc_string}', end='  \n')

    def _try_colors(self):
        self.bot.say(color.white('white'))
        self.bot.say(color.black('black'))
        self.bot.say(color.blue('blue'))
        self.bot.say(color.green('green'))
        self.bot.say(color.light_red('light_red'))
        self.bot.say(color.red('red'))
        self.bot.say(color.purple('purple'))
        self.bot.say(color.orange('orange'))
        self.bot.say(color.yellow('yellow'))
        self.bot.say(color.light_green('light_green'))
        self.bot.say(color.cyan('cyan'))
        self.bot.say(color.light_cyan('light_cyan'))
        self.bot.say(color.light_blue('light_blue'))
        self.bot.say(color.pink('pink'))
        self.bot.say(color.gray('gray'))
        self.bot.say(color.light_grey('light_grey'))