import logging
import re
from functools import wraps

import pybot


class plugin:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    def on_welcome(self, connection, raw_msg):
        """
        called by bot when connected to channel
        """
        pass

    def on_pubmsg(self, connection, raw_msg):
        """
        called by bot when public msg received
        """
        pass

    def on_kick(self, connection, raw_msg):
        """
        called by bot when kicked from channel
        """
        pass

    def on_privmsg(self, connection, raw_msg):
        """
        called by bot when private msg received
        """
        pass

    def get_help(self):
        pass

    # see https://www.alien.net.au/irc/irc2numerics.html
    # for deep explaination
    def on_whoisuser(self, connection, raw_msg):
        pass

    def on_nicknameinuse(self, connection, raw_msg):
        """ called by super() when given nickname is reserved """
        pass


def command(func):
    if not hasattr(func, '__command'):
        func.__command = True

    return func


def admin(function):
    @wraps(function)
    def admin_function(self, sender_nick, *args):
        if sender_nick in pybot.pybot.ops or sender_nick == 'pingwindyktator':  # E HEHE
            function(self, sender_nick, *args)

    return admin_function
