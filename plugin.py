import logging
import utils

from pybot import irc_nickname
from color import color
from functools import wraps



class plugin:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(self._get_class_name())
        self.config = self.bot.config[self._get_class_name()] if self._get_class_name() in self.bot.config else None

    def _get_class_name(self):
        return self.__class__.__name__

    def on_welcome(self, *args, **kwargs):
        """
        called by bot when connected to server
        raw_msg  - raw IRC msg
        server   - server address
        port     - server's port
        nickname - bot's nickname
        """
        pass

    def on_disconnect(self, *args, **kwargs):
        """
        called by bot when disconnected from server
        raw_msg - raw IRC msg
        server  - server address
        port    - server's port
        """
        pass

    def on_join(self, *args, **kwargs):
        """
        called by bot when somebody joins channel
        raw_msg - raw IRC msg
        source  - source of joined person
        """
        pass

    def on_me_joined(self, *args, **kwargs):
        """
        called by bot when joined channel
        raw_msg - raw IRC msg
        channel - channel
        """
        pass

    def on_pubmsg(self, *args, **kwargs):
        """
        called by bot when public msg received
        raw_msg - raw IRC msg
        source  - pubmsg source
        msg     - full message
        """
        pass

    def on_kick(self, *args, **kwargs):
        """
        called by bot when somebody got kicked
        raw_msg - raw IRC msg
        who     - person who gets kicked
        source  - kicker's source
        """
        pass

    def on_me_kicked(self, *args, **kwargs):
        """
        called by bot when kicked from channel
        raw_msg - raw IRC msg
        source  - kicker's source
        """
        pass

    def on_privmsg(self, *args, **kwargs):
        """
        called by bot when private msg received
        raw_msg - raw IRC msg
        msg     - full message
        source  - primsg source
        """
        pass

    # see https://www.alien.net.au/irc/irc2numerics.html
    # for deep explanation
    def on_whoisuser(self, *args, **kwargs):
        """
        called by bot when /whois response received
        raw_msg - raw IRC msg
        nick    - requested nickname
        user    - requested username
        host    - requested hostname
        """
        pass

    def on_nicknameinuse(self, *args, **kwargs):
        """
        called by bot when given nickname is reserved
        raw_msg       - raw IRC msg
        busy_nickname - nickname bot was trying to use
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
            self.logger.error(f'exception caught calling {function}: {e}')
            if self.bot.is_debug_mode_enabled(): raise

    command_impl.__command = True
    return command_impl


def doc(doc_string):
    def doc_impl(function):
        function.__doc_string = doc_string.strip()
        return function

    return doc_impl


def admin(function):
    @wraps(function)
    def admin_impl(self, sender_nick, **kwargs):
        sender_nick = irc_nickname(sender_nick)
        if sender_nick in self.bot.config['ops']:
            function(self, sender_nick=sender_nick, **kwargs)
        else:
            self.logger.info(f'{sender_nick} is not op, skipping command')

    return admin_impl
