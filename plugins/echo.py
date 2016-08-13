import re

import msg_parser
from plugin import *


class echo(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    def on_pubmsg(self, connection, raw_msg):
        full_msg = raw_msg.arguments[0]
        command = msg_parser.trim_msg(self.bot.get_command_prefix(), full_msg)
        commands = msg_parser.split_msg(command)

        if len(commands) > 0 and commands[0] == 'echo':
            to_trim = re.compile('echo *').findall(command)[0]
            response = command.replace(to_trim, '', 1)
            self.bot.send_response_to_channel(response)
            self.logger.info("echo '%s' for %s" % (response, raw_msg.source.nick))
