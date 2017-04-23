import importlib
import sys

from plugin import *


class plugin_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    @admin
    def disable_plugin(self, sender_nick, args, **kwargs):
        plugins = {}  # plugin_name -> plugin_instance
        for p in self.bot.get_plugins(): plugins[type(p).__name__] = p

        for arg in args:
            if arg not in plugins:
                self.bot.say('not such plugin: [%s]' % arg)
            else:
                cmds = self.bot.get_plugin_commands(arg)
                plugins[arg].unload_plugin()
                self.bot.plugins.remove(plugins[arg])
                for cmd in cmds:
                    del self.bot.commands[cmd]

                self.bot.say('plugin [%s] disabled with commands %s' % (arg, cmds))
                self.logger.warning('plugin [%s] disabled with commands %s by %s' % (arg, cmds, sender_nick))

    @command
    def plugins(self, sender_nick, **kwargs):
        self.bot.say('enabled plugins: %s' % self.bot.get_plugins_names())
        self.logger.info('plugins given to %s' % sender_nick)

    @command
    @admin
    def enable_plugin(self, sender_nick, args, **kwargs):
        plugins = {}  # plugin_name -> plugin_class
        for plugin_class in plugin.__subclasses__():
            plugins[plugin_class.__name__] = plugin_class

        for arg in args:
            if arg not in plugins:
                self.bot.say('not such plugin: [%s]' % arg)
            else:
                p = plugins[arg](self.bot)
                self.bot.register_plugin(p)
                self.bot.register_commands_for_plugin(p)
                cmds = self.bot.get_plugin_commands(type(p).__name__)
                self.bot.say('plugin [%s] enabled with commands %s' % (arg, cmds))
                self.logger.warning('plugin [%s] enabled with commands %s by %s' % (arg, cmds, sender_nick))

    @command
    @admin
    def load_plugin(self, sender_nick, args, **kwargs):
        """
        Loads **new** module.
        """
        args = [x for x in args if x not in self.bot.get_plugins_names()]

        for arg in args:
            try:
                # loading module
                new_module = importlib.import_module('plugins.' + arg)
                plugin_class = getattr(new_module, arg)  # requires plugin class' name to be equal to module name

                # loading plugin
                new_class_instance = plugin_class(self.bot)
                self.bot.register_plugin(new_class_instance)
                self.bot.register_commands_for_plugin(new_class_instance)
                self.logger.warning('plugin [%s] loaded by %s' % (plugin_class.__name__, sender_nick))
                self.bot.say('plugin [%s] loaded' % arg)
            except Exception as e:
                self.logger.error('exception caught while loading plugin [%s] by %s: %s' % (plugin_class.__name__, sender_nick, e))
                self.bot.say('exception caught while reloading plugin [%s]' % plugin_class.__name__)

    @command
    @admin
    def reload_plugin(self, sender_nick, args, **kwargs):
        """
        Will cause reference leak! There's no possibility to fully unload module in python.
        Old module's class instance will be fixed in memory after this command.

        Reloading module has to be enabled before this command is executed.
        """
        args = [x for x in args if x in self.bot.get_plugins_names()]  # plugins asked to be reloaded

        if self.__class__.__name__ in args:  # THIS plugin cannot be reloaded!
            self.bot.say('plugin %s cannot be reloaded' % self.__class__.__name__)
            args.remove(self.__class__.__name__)

        plugin_name_to_instance = {}  # plugin_name -> plugin_instance
        for p in self.bot.get_plugins(): plugin_name_to_instance[type(p).__name__] = p

        plugins_to_reload = [type(plugin_instance) for plugin_instance in self.bot.get_plugins() if type(plugin_instance).__name__ in args]  # classes to reload

        for plugin_class in plugins_to_reload:
            try:
                plugin_instance = plugin_name_to_instance[plugin_class.__name__]
                # unloading plugin
                cmds = self.bot.get_plugin_commands(plugin_class.__name__)
                plugin_instance.unload_plugin()
                self.bot.plugins.remove(plugin_instance)
                for cmd in cmds: del self.bot.commands[cmd]

                # reloading module
                del plugin_instance
                sys.modules[plugin_class.__module__] = importlib.reload(sys.modules[plugin_class.__module__])
                plugin_class = getattr(sys.modules[plugin_class.__module__], plugin_class.__name__)  # requires plugin class' name to be equal to module name

                # loading plugin
                new_class_instance = plugin_class(self.bot)
                self.bot.register_plugin(new_class_instance)
                self.bot.register_commands_for_plugin(new_class_instance)
                self.logger.warning('plugin [%s] reloaded by %s' % (plugin_class.__name__, sender_nick))
                self.bot.say('plugin [%s] reloaded' % plugin_class.__name__)
            except Exception as e:
                self.logger.error('exception caught while reloading plugin [%s] by %s: %s' % (plugin_class.__name__, sender_nick, e))
                self.bot.say('exception caught while reloading plugin [%s]' % plugin_class.__name__)
