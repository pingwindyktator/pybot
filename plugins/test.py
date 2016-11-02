from plugin import *


class test(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.res = 'jjjj'

    def on_pubmsg(self, connection, raw_msg):
        self.bot.send_response_to_channel(self.res)


