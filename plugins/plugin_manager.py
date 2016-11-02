import importlib

import sys

from plugin import *


class plugin_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    @admin
    def disable_plugin(self, sender_nick, args):
        plugins = {}  # plugin_name -> plugin_instance
        for p in self.bot.get_plugins():
            plugins[type(p).__name__] = p

        for arg in args:
            if arg not in plugins:
                self.bot.send_response_to_channel('not such plugin: [%s]' % arg)
            else:
                cmds = self.bot.get_plugin_commands(arg)
                self.bot.plugins.remove(plugins[arg])
                for cmd in cmds:
                    del self.bot.commands[cmd]

                self.bot.send_response_to_channel('plugin [%s] disabled with commands %s' % (arg, cmds))
                self.logger.warn('plugin [%s] disabled with commands %s by %s' % (arg, cmds, sender_nick))

    @command
    def plugins(self, sender_nick, args):
        self.bot.send_response_to_channel('enabled plugins: %s' % self.bot.get_plugins_names())
        self.logger.info('plugins given to %s' % sender_nick)

    @command
    @admin
    def enable_plugin(self, sender_nick, args):
        plugins = {}  # plugin_name -> plugin_class
        for plugin_class in plugin.__subclasses__():
            plugins[plugin_class.__name__] = plugin_class

        for arg in args:
            if arg not in plugins:
                self.bot.send_response_to_channel('not such plugin: [%s]' % arg)
            else:
                p = plugins[arg](self.bot)
                self.bot.register_plugin(p)
                self.bot.register_commands_for_plugin(p)
                cmds = self.bot.get_plugin_commands(type(p).__name__)
                self.bot.send_response_to_channel('plugin [%s] enabled with commands %s' % (arg, cmds))
                self.logger.warn('plugin [%s] enabled with commands %s by %s' % (arg, cmds, sender_nick))

    @command
    @admin
    def reload_plugin(self, sender_nick, args):
        args = [x for x in args if x in self.bot.get_plugins_names()]
        self.reload_modules(args)
        self.load_plugins(args)

    def reload_modules(self, args):
        if self.__class__.__name__ in args:
            self.bot.send_response_to_channel('plugin %s cannot be reloaded' % self.__class__.__name__)
            args.remove(self.__class__.__name__)

        plugin_name_to_instance = {}  # plugin_name -> plugin_instance
        for p in self.bot.get_plugins():
            plugin_name_to_instance[type(p).__name__] = p

        plugins_to_reload = [plugin_class for plugin_class in plugin.__subclasses__() if plugin_class.__name__ in args]
        for plugin_class in plugins_to_reload:
            # unloading plugin
            # self.disable_plugin(sender_nick, [plugin_class.__name__])
            cmds = self.bot.get_plugin_commands(plugin_class.__name__)
            self.bot.plugins.remove(plugin_name_to_instance[plugin_class.__name__])
            for cmd in cmds:
                del self.bot.commands[cmd]

            # reloading module
            del plugin_name_to_instance[plugin_class.__name__]
            importlib.reload(sys.modules[plugin_class.__module__])
            print(42)

    def load_plugins(self, args):
        # reloading classes from reloaded module
        plugins_to_reload = [plugin_class for plugin_class in plugin.__subclasses__() if plugin_class.__name__ in args]
        for plugin_class in plugins_to_reload:
            # loading plugin
            # self.enable_plugin(sender_nick, [plugin_class.__name__])
            p = plugin_class(self.bot)
            self.bot.register_plugin(p)
            self.bot.register_commands_for_plugin(p)
            self.bot.send_response_to_channel('plugin %s reloaded' % plugin_class.__name__)
