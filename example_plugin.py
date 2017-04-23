from plugin import *


class example_plugin(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    def unload_plugin(self):
        # you should unload your plugin in this method
        pass

    @command
    def example_command(self, sender_nick, **kwargs):
        self.logger.info('example command called by %s' % sender_nick)
        self.bot.send_response_to_channel('example command called!')
        # you can easily access everything you need from self.bot
        # see also plugin base class methods for more information
        #
        # every command should take **kwargs argument(!) and positional ones as needed:
        #   sender_nick - nickname of msg sender
        #   cmd_list    - ['some', 'arguments', 'passed', 'to', 'plugin']
        #   raw_cmd     - 'some   arguments passes to plugin   '
        #   raw_msg     - raw IRC msg

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
