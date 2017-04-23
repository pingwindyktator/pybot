from plugin import *


class example_plugin(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    def unload_plugin(self):
        # you should unload your plugin in this method
        pass

    @command
    def example_command(self, sender_nick, args, **kwargs):
        self.logger.info('example command called by %s with %s' % (sender_nick, args))
        self.bot.send_response_to_channel('example command called!')
        # you can easily access everything you need from self.bot
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
