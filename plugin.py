import logging
import re
import sys
import utils

from utils import irc_nickname
from pybot import pybot
from color import color
from functools import wraps


class plugin:
    def __init__(self, bot: pybot):
        self.bot = bot
        self.logger = logging.getLogger(self._get_class_name())
        self.config = self.bot.config[self._get_class_name()] if self._get_class_name() in self.bot.config else None

    def _get_class_name(self):
        return self.__class__.__name__

    def on_welcome(self, raw_msg, server, port, nickname, **kwargs):
        """
        called by bot when connected to server
        :param raw_msg  - raw IRC msg
        :param server   - server address
        :param port     - server's port
        :param nickname - bot's nickname
        """

    def on_disconnect(self, raw_msg, server, port, **kwargs):
        """
        called by bot when disconnected from server
        :param raw_msg - raw IRC msg
        :param server  - server address
        :param port    - server's port
        """

    def on_join(self, raw_msg, source, **kwargs):
        """
        called by bot when somebody joins channel
        :param raw_msg - raw IRC msg
        :param source  - source of joined user
        """

    def on_me_joined(self, raw_msg, **kwargs):
        """
        called by bot when joined channel
        :param raw_msg - raw IRC msg
        """

    def on_pubmsg(self, raw_msg, source, msg, **kwargs):
        """
        called by bot when public msg received
        :param raw_msg - raw IRC msg
        :param source  - pubmsg source
        :param msg     - full message
        """

    def on_kick(self, raw_msg, who, source, **kwargs):
        """
        called by bot when somebody got kicked
        :param raw_msg - raw IRC msg
        :param who     - person who gets kicked
        :param source  - kicker's source
        """

    def on_me_kicked(self, raw_msg, source, **kwargs):
        """
        called by bot when kicked from channel
        :param raw_msg - raw IRC msg
        :param source  - kicker's source
        """
        pass

    def on_privmsg(self, raw_msg, msg, source, **kwargs):
        """
        called by bot when private msg received
        :param raw_msg - raw IRC msg
        :param msg     - full message
        :param source  - primsg source
        """
    # test
    # see https://www.alien.net.au/irc/irc2numerics.html
    # for deep explanation
    def on_whoisuser(self, raw_msg, nick, user, host, **kwargs):
        """
        called by bot when /whois response received
        :param raw_msg - raw IRC msg
        :param nick    - requested nickname
        :param user    - requested username
        :param host    - requested hostname
        """

    def on_nicknameinuse(self, raw_msg, busy_nickname, **kwargs):
        """
        called by bot when given nickname is reserved
        :param raw_msg       - raw IRC msg
        :param busy_nickname - nickname bot was trying to use
        """

    def on_nick(self, raw_msg, source, old_nickname, new_nickname, **kwargs):
        """
        called by bot when somebody changes nickname
        :param raw_msg      - raw IRC msg
        :param source       - changer's source (with old nickname!)
        :param old_nickname - old nickname
        :param new_nickname - new nickname
        """

    def on_part(self, raw_msg, source, **kwargs):
        """
        called by bot when somebody lefts channel
        :param raw_msg - raw IRC msg
        :param source  - source of left user
        """

    def on_quit(self, raw_msg, source, **kwargs):
        """
        called by bot when somebody disconnects from IRC server
        :param raw_msg - raw IRC msg
        :param source  - source of disconnected user
        """

    def on_ctcp(self, raw_msg, source, msg, **kwargs):
        """
        called by bot when ctcp arrives (/me ...)
        :param raw_msg - raw IRC msg
        :param source  - source of ctcped user
        :param msg     - ctcp message
        """

    def on_namreply(self, raw_msg, nicknames, **kwargs):
        """
        called by bot when names response arrives
        :param raw_msg   - raw IRC msg
        :param nicknames - nicknames in channel
        """
        pass

    def unload_plugin(self):
        """
        called when plugin needs to be disabled / reloaded 
        """
        pass


def command(function):
    @wraps(function)
    def command_impl(self, **kwargs):
        try:
            function(self, **kwargs)
        except Exception as e:
            self.logger.error(f'exception caught calling {function.__qualname__}: {e}')
            self.bot.say('internal error, sorry :(')
            if self.bot.is_debug_mode_enabled(): raise

    if hasattr(command_impl, '__regex'):
        print(f'function {function.__qualname__} already registered as regex handler')
        sys.exit(8)

    command_impl.__command = True
    return command_impl


def on_message(regex_str):
    def on_message_impl(function):
        @wraps(function)
        def on_message_impl_impl(self, **kwargs):
            try:
                function(self, **kwargs)
            except Exception as e:
                self.logger.error(f'exception caught calling {function.__qualname__}: {e}')
                if self.bot.is_debug_mode_enabled(): raise

        if hasattr(on_message_impl_impl, '__command'):
            print(f'function {function.__qualname__} already registered as command')
            sys.exit(7)
        try:
            on_message_impl_impl.__regex = re.compile(regex_str)
            return on_message_impl_impl
        except Exception as e:
            print(f'invalid regex for regex handler {function.__qualname__}: {e}')
            sys.exit(5)

    return on_message_impl


def doc(doc_string):
    def doc_impl(obj):
        obj.__doc_string = doc_string.strip()
        return obj

    return doc_impl


def admin(function):
    @wraps(function)
    def admin_impl(self, sender_nick, **kwargs):
        sender_nick = irc_nickname(sender_nick)
        if sender_nick in self.bot.config['ops']:
            function(self, sender_nick=sender_nick, **kwargs)
        else:
            self.logger.info(f'{sender_nick} is not op, skipping command')

    admin_impl.__admin = True
    return admin_impl
