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
        called by bot when connected to server
        """
        pass

    def on_join(self, connection, raw_msg):
        """
        called by bot when somebody joins channel
        """
        pass

    def on_me_joined(self, connection, raw_msg):
        """
        called by bot when joined channel
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

    # see https://www.alien.net.au/irc/irc2numerics.html
    # for deep explanation
    def on_whoisuser(self, connection, raw_msg):
        """
        called by bot when /whois response received 
        """
        pass

    def on_nicknameinuse(self, connection, raw_msg):
        """
        called by bot when given nickname is reserved
        """
        pass


def command(function):
    @wraps(function)
    def command_impl(self, *args):
        try:
            function(self, *args)
        except Exception as e:
            self.logger.warn('exception caught calling %s: %s' % (function, e))

    command_impl.__command = True
    return command_impl


def doc(doc_string):
    def doc_impl(function):
        function.__doc_string = doc_string
        return function

    return doc_impl


def admin(function):
    @wraps(function)
    def admin_impl(self, sender_nick, *args):
        if sender_nick in pybot.pybot.ops or sender_nick == 'pingwindyktator':  # E HEHE
            function(self, sender_nick, *args)

    return admin_impl
