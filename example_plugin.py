from plugin import *

# TIPS:
# - all plugin functions will be called from one, main thread
# - IRC nickname is case-insensitive. Generally you should'nt worry about it, since pybot API uses irc_nickname class
#     to represent it, but - for example - if you wan't to use database, use .casefold()


class example_plugin(plugin):  # plugin class name should equal module name!
    def __init__(self, bot):
        super().__init__(bot)

    def unload_plugin(self):
        # you should unload your plugin in this method
        # usually you don't need to implement this
        pass

    @command
    def example_command(self, sender_nick, args, **kwargs):
        self.logger.info(f'example command called by {sender_nick} with {args}')
        self.bot.say('example command called!')
        self.bot.say('private msg', sender_nick)
        # you can easily access everything you need from self.bot
        # you can access plugin's config file section via self.config and whole config via self.bot.config
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
