from plugin import *

# TIPS:
# - all plugin functions will be called from one, main thread
# - IRC nickname is case-insensitive. Usually you should'nt worry about it, since pybot API uses irc_nickname class
#     to represent it, but - for example - if you wan't to use database, use .casefold()
# - All exceptions from commands and from on_* methods will be caught by bot - nothing bad will happen
# - If your __init__ throws, plugin won't be loaded by bot. You can use it to assert environment compatibility
# - Plugin class name should be equal to module name
# - Message you'd get ('msg', 'args' arguments) might be empty
# - Help docs should follow docopt standard (see http://docopt.org)


@doc("this is what you will see as plugin's help")
class example_plugin(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    def unload_plugin(self):
        # you should unload your plugin in this method
        # usually you don't need to implement this
        pass

    def assert_config(self):
        # assert config compatibility here
        # should throw utils.config_error if config is invalid (see utils.c_assert_error)
        # in such case, plugin won't be loaded
        #
        # ex: utils.c_assert_error(config['port'] >= 1024, 'port should be >= 1024')
        pass

    @command
    def example_command(self, sender_nick, args, **kwargs):
        self.logger.info(f'example command called by {sender_nick} with {args}')
        self.bot.say('example command called!')
        self.bot.say(f'{color.red("whoa, red answer")} and normal one')
        self.bot.say('private msg', sender_nick)
        # you can easily access everything you need from self.bot
        # you can access plugin's config file section via self.config and whole config via self.bot.config
        # self.config is simply self.bot.config['your_plugin's_name']
        #
        # every command should take **kwargs argument(!) and positional ones as needed:
        #   sender_nick - nickname of msg sender
        #   args        - ['some', 'arguments', 'passed', 'to', 'plugin']
        #   msg         - 'some   arguments passes to plugin   '
        #   raw_msg     - raw IRC msg

    def on_pubmsg(self, raw_msg, **kwargs):
        # see plugin base class methods for more on_* methods
        #
        # every on_* method should take **kwargs argument(!) and positional ones as needed
        # see plugin base class for possible positional arguments
        pass

    @command
    @admin
    def example_admin_command(self, sender_nick, **kwargs):
        # you need admin privileges to call this command
        pass

    @command
    @doc("this is what you will see as command's help")
    def example_command_with_doc(self, sender_nick, **kwargs):
        # try '.help example_command_with_doc' to see "this is what you will see as command's help"
        pass
