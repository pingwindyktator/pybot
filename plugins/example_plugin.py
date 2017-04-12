from plugin import *


class example_plugin(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def example_command(self, sender_nick, args):
        self.logger.info('example command called by %s' % sender_nick)
        self.bot.send_response_to_channel('example command called!')
        # you can easily access everything you need from self.bot
        # see also plugin base class methods for more information

    @command
    @admin
    def example_admin_command(self, sender_nick, args):
        # you need admin privileges to call this command
        pass

    @command
    @doc("this is what you will see as command's help")
    def example_command_with_doc(self, sender_nick, args):
        # try '.help example_command_with_doc' to see "this is what you will see as command's help"
        pass
