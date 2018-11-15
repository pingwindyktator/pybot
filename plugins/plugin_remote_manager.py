import importlib
import sys

from fuzzywuzzy import process, fuzz
from plugin import *


class plugin_remote_manager(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    class no_plugins_module_found(Exception):
        pass

    class plugin_not_enabled(Exception):
        pass

    class plugin_already_enabled(Exception):
        pass

    @command
    @doc('get enabled plugins')
    def plugins(self, sender_nick, **kwargs):
        self.bot.say(f'enabled plugins: {", ".join(sorted(self.bot.get_plugins_names()))}')
        self.logger.info(f'plugins given to {sender_nick}')

    def get_best_plugin_name_match(self, plugin_name):
        choices = [p.replace('_', ' ') for p in self.bot.get_plugins_names()]
        plugin_name = plugin_name.replace('_', ' ')
        result = process.extract(plugin_name, choices, scorer=fuzz.token_sort_ratio)
        result = [(r[0].replace(' ', '_'), r[1]) for r in result]
        return result[0][0] if result[0][1] > 65 else None

    @command(admin=True)
    @doc('enable_plugin <name>: enable <name> plugin from loaded module')
    def enable_plugin(self, sender_nick, args, **kwargs):
        if not args: return
        plugin_name = args[0]
        self.logger.warning(f'enabling {plugin_name} plugin for {sender_nick}')

        try:
            self.enable_plugin_impl(plugin_name)
            self.bot.say(f'plugin {plugin_name} enabled')
        except self.no_plugins_module_found as e:
            self.logger.info(e)
            fixed_command = f'load_plugin {plugin_name}'
            self.bot.say(f'no such plugin: {plugin_name}, use \'{self.bot.get_command_prefix()}{fixed_command}\' to load new plugin')
            self.bot.register_fixed_command(fixed_command)
        except self.plugin_already_enabled as e:
            self.logger.info(e)
            fixed_command = f'load_plugin {plugin_name}'
            self.bot.say(f'plugin already enabled, use \'{self.bot.get_command_prefix()}{fixed_command}\' to reload it')
            self.bot.register_fixed_command(fixed_command)
        except Exception as e:
            self.logger.error(f'exception caught while trying to enable plugin {plugin_name}: {type(e).__name__}: {e}')
            self.bot.say(f'cannot enable {plugin_name}: unexpected exception thrown')
            if self.bot.is_debug_mode_enabled(): raise
            else: utils.report_error()

    @command(admin=True)
    @doc('disable_plugin <name>: unload and disable enabled <name> plugin')
    def disable_plugin(self, sender_nick, args, **kwargs):
        if not args: return
        plugin_name = args[0]
        self.logger.warning(f'disabling {plugin_name} plugin for {sender_nick}')

        try:
            self.disable_plugin_impl(plugin_name)
            self.bot.say(f'plugin {plugin_name} disabled')
        except self.plugin_not_enabled as e:
            self.logger.info(e)
            self.bot.say(f'no such enabled plugin: {plugin_name}')
        except Exception as e:
            self.logger.error(f'exception caught while trying to disable plugin {plugin_name}: {type(e).__name__}: {e}')
            self.bot.say(f'cannot disable {plugin_name}: unexpected exception thrown')
            if self.bot.is_debug_mode_enabled(): raise
            else: utils.report_error()

    def enable_plugin_impl(self, name):
        """
        module has to be loaded!
        """

        enabled_plugins = {}  # plugin_name -> plugin_instance
        for p in self.bot.get_plugins(): enabled_plugins[type(p).__name__] = p

        if name in enabled_plugins: raise self.plugin_already_enabled(f'cannot enable {name}: plugin already enabled')
        if f'plugins.{name}' not in sys.modules: raise self.no_plugins_module_found(f'cannot enable {name}: no loaded module plugins.{name} found')
        plugin_class = getattr(sys.modules[f'plugins.{name}'], name)  # requires plugin class' name to be equal to module name
        new_class_instance = plugin_class(self.bot)
        self.bot.register_plugin(new_class_instance)
        self.logger.warning(f'plugin {name} enabled')

    def disable_plugin_impl(self, name):
        """
        plugin has to be enabled!
        """

        enabled_plugins = {}  # plugin_name -> plugin_instance
        for p in self.bot.get_plugins(): enabled_plugins[type(p).__name__] = p
        if name not in enabled_plugins: raise self.plugin_not_enabled(f'Cannot disable {name}: plugin is not enabled or does not exist')
        plugin_instance = enabled_plugins[name]
        self.bot.remove_plugin(plugin_instance)
        self.logger.warning(f'plugin {name} disabled')

    @command(admin=True)
    @doc('load_plugin <name>: load new plugin or reload existing one')
    def load_plugin(self, sender_nick, args, **kwargs):
        if not args: return
        plugin_name = args[0]
        self.logger.warning(f'loading {plugin_name} plugin for {sender_nick}')

        # modules loaded by python
        # e.g. ['plugins.man', 'plugins.stalker']
        loaded_modules = [x for x in sys.modules.keys() if x.startswith('plugins.')]

        # plugin_name -> plugin_instance
        # plugins enabled by bot - should be "subset" of loaded_modules
        # some modules can be loaded but not enabled by bot
        # e.g. {'man': plugins.man object at..., 'stalker': plugins.stalker object at...}
        enabled_plugins = {}
        for p in self.bot.get_plugins(): enabled_plugins[type(p).__name__] = p

        try:
            if self.__class__.__name__ == plugin_name:  # THIS plugin cannot be reloaded!
                self.bot.say(f'plugin {self.__class__.__name__} cannot be reloaded')
                return

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

        except (self.no_plugins_module_found, ImportError, ModuleNotFoundError) as e:  # user error #1
            self.logger.info(f'exception caught while trying to load plugin {plugin_name}: {type(e).__name__}: {e}')
            response = f'cannot find {plugin_name}'
            possible_name = self.get_best_plugin_name_match(plugin_name) if self.config['try_autocorrect'] else None
            if possible_name:
                fixed_command = f'load_plugin {possible_name}'
                response = f'{response}, did you mean {possible_name}?'
                self.bot.register_fixed_command(fixed_command)

            self.bot.say(response)

        except self.plugin_not_enabled as e:  # user error #2
            self.logger.info(f'exception caught while trying to load plugin {plugin_name}: {type(e).__name__}: {e}')
            self.bot.say(f'cannot disable {plugin_name}, plugin is not enabled')

        except (Exception, self.plugin_already_enabled) as e:  # implementation error
            self.logger.error(f'exception caught while trying to load plugin {plugin_name}: {type(e).__name__}: {e}')
            self.bot.say(f'cannot load {plugin_name}: unexpected exception thrown')
            if self.bot.is_debug_mode_enabled(): raise
            else: utils.report_error()
