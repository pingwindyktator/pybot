import importlib
import inspect
import sys

from plugin import *


class plugin_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    class NoPluginsModuleFound(Exception):
        pass

    class PluginNotEnabled(Exception):
        pass

    class PluginAlreadyEnabled(Exception):
        pass

    @command
    @doc('get enabled plugins')
    def plugins(self, sender_nick, **kwargs):
        self.bot.say(f'enabled plugins: {self.bot.get_plugins_names()}')
        self.logger.info(f'plugins given to {sender_nick}')

    @command
    @admin
    @doc('enable_plugin <name>...: enable <name> plugin from loaded module')
    def enable_plugin(self, sender_nick, args, **kwargs):
        if not args: return
        self.logger.warning(f'enabling {args} plugins for {sender_nick}')

        for arg in args:
            try:
                self.enable_plugin_impl(arg)
                self.bot.say(f'plugin {arg} enabled')
            except self.NoPluginsModuleFound as e:
                self.logger.info(e)
                self.bot.say(f'no such plugin: {arg}, use \'{self.bot.config["command_prefix"]}load_plugin {arg}\' to load new plugin')
            except self.PluginAlreadyEnabled as e:
                self.logger.info(e)
                self.bot.say(f'plugin already enabled, use \'{self.bot.config["command_prefix"]}load_plugin {arg}\' to reload it')
            except Exception as e:
                self.logger.error(f'exception caught while trying to enable plugin {arg}: {e}')
                self.bot.say(f'cannot enable {arg}: unexpected exception thrown')
                if self.bot.is_debug_mode_enabled(): raise

    @command
    @admin
    @doc('disable_plugin <name>...: unload and disable enabled <name> plugin')
    def disable_plugin(self, sender_nick, args, **kwargs):
        if not args: return
        self.logger.warning(f'disabling {args} plugins for {sender_nick}')

        for arg in args:
            try:
                self.disable_plugin_impl(arg)
                self.bot.say(f'plugin {arg} disabled')
            except self.PluginNotEnabled as e:
                self.logger.info(e)
                self.bot.say(f'no such enabled plugin: {arg}')
            except Exception as e:
                self.logger.error(f'exception caught while trying to disable plugin {arg}: {e}')
                self.bot.say(f'cannot disable {arg}: unexpected exception thrown')
                if self.bot.is_debug_mode_enabled(): raise

    def enable_plugin_impl(self, name):
        """
        module has to be loaded! 
        """
        enabled_plugins = {}
        for p in self.bot.get_plugins(): enabled_plugins[type(p).__name__] = p

        if name in enabled_plugins: raise self.PluginAlreadyEnabled(f'Cannot enable {name}: plugin already enabled')
        if f'plugins.{name}' not in sys.modules: raise self.NoPluginsModuleFound(f'Cannot enable {name}: no loaded module plugins.{name} found')
        plugin_class = getattr(sys.modules[f'plugins.{name}'], name)  # requires plugin class' name to be equal to module name
        new_class_instance = plugin_class(self.bot)
        self.bot.register_plugin(new_class_instance)
        self.logger.warning(f'plugin {name} enabled')

    def disable_plugin_impl(self, name):
        """
        plugin has to be enabled! 
        """

        enabled_plugins = {}
        for p in self.bot.get_plugins(): enabled_plugins[type(p).__name__] = p
        if name not in enabled_plugins: raise self.PluginNotEnabled(f'Cannot disable {name}: plugin is not enabled or does not exist')
        plugin_instance = enabled_plugins[name]
        plugin_class = type(plugin_instance)
        cmds = self.bot.get_plugin_commands(plugin_class.__name__)

        try:
            plugin_instance.unload_plugin()
        except Exception as e:
            self.logger.error(f'{name}.unload_plugin() throws: {e}. continuing anyway...')

        self.bot.plugins.remove(plugin_instance)

        # using copy and update here
        commands_copy = self.bot.commands.copy()
        for cmd in cmds: del commands_copy[cmd]

        msg_regexes_copy = self.bot.msg_regexes.copy()
        for f in inspect.getmembers(plugin_instance, predicate=inspect.ismethod):
            func = f[1]
            __regex = getattr(func, '__regex') if hasattr(func, '__regex') else None
            if (__regex) and (__regex in msg_regexes_copy) and (func in msg_regexes_copy[__regex]): msg_regexes_copy[__regex].remove(func)

        self.bot.commands = commands_copy
        self.bot.msg_regexes = msg_regexes_copy
        self.logger.warning(f'plugin {name} disabled with commands {cmds}')

    @command
    @admin
    @doc('load_plugin <name>...: load new plugin or reload existing one')
    def load_plugin(self, sender_nick, args, **kwargs):
        if not args: return
        self.logger.warning(f'loading {args} plugins for {sender_nick}')

        # modules loaded by python
        # e.g. ['plugins.man', 'plugins.stalker']
        loaded_modules = [x for x in sys.modules.keys() if x.startswith('plugins.')]

        # plugin_name -> plugin_instance
        # plugins enabled by bot - should be "subset" of loaded_modules
        # some modules can be loaded but not enabled by bot
        # e.g. {'man': plugins.man object at..., 'stalker': plugins.stalker object at...}
        enabled_plugins = {}
        for p in self.bot.get_plugins(): enabled_plugins[type(p).__name__] = p

        for plugin_name in args:
            try:
                if self.__class__.__name__ == plugin_name:  # THIS plugin cannot be reloaded!
                    self.bot.say(f'plugin {self.__class__.__name__} cannot be reloaded')
                    continue

                if f'plugins.{plugin_name}' in loaded_modules:
                    """
                    Will cause reference leak! There's no possibility to fully unload module in python.
                    Old module's class instance will be fixed in memory after this command.
                    """

                    if plugin_name in enabled_plugins:
                        self.disable_plugin_impl(plugin_name)  # disabling plugin
                        del enabled_plugins[plugin_name]  # freeing plugin instance reference
                        sys.modules[f'plugins.{plugin_name}'] = importlib.reload(sys.modules[f'plugins.{plugin_name}'])  # reloading module
                        self.logger.warning(f'module plugins.{plugin_name} reloaded')
                        self.enable_plugin_impl(plugin_name)  # enabling plugin
                        self.bot.say(f'plugin {plugin_name} reloaded and enabled')

                    else:
                        sys.modules[f'plugins.{plugin_name}'] = importlib.reload(sys.modules[f'plugins.{plugin_name}'])  # reloading module
                        self.logger.warning(f'module plugins.{plugin_name} reloaded')
                        self.bot.say(f"plugin {plugin_name} reloaded, but it's not enabled")

                else:
                    importlib.import_module(f'plugins.{plugin_name}')  # loading new module
                    self.logger.warning(f'module plugins.{plugin_name} loaded')
                    self.enable_plugin_impl(plugin_name)  # enabling plugin
                    self.bot.say(f'plugin {plugin_name} loaded and enabled')

            except (self.NoPluginsModuleFound, ImportError, ModuleNotFoundError) as e:  # user error #1
                self.logger.info(e)
                self.bot.say(f'cannot enable {plugin_name}, no appropriate module found')

            except self.PluginNotEnabled as e:  # user error #2
                self.logger.info(e)
                self.bot.say(f'cannot disable {plugin_name}, plugin is not enabled')

            except (Exception, self.PluginAlreadyEnabled) as e:  # implementation error
                self.logger.error(f'exception caught while trying to load plugin {plugin_name}: {e}')
                self.bot.say(f'cannot load {plugin_name}: unexpected exception thrown')
                if self.bot.is_debug_mode_enabled(): raise
