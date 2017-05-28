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

    def on_welcome(self, **kwargs):
        """
        called by bot when connected to server
        raw_msg  - raw IRC msg
        server   - server address
        port     - server's port
        nickname - bot's nickname
        """
        pass

    def on_disconnect(self, **kwargs):
        """
        called by bot when disconnected from server
        raw_msg - raw IRC msg
        server  - server address
        port    - server's port
        """
        pass

    def on_join(self, **kwargs):
        """
        called by bot when somebody joins channel
        raw_msg - raw IRC msg
        source  - source of joined user
        """
        pass

    def on_me_joined(self, **kwargs):
        """
        called by bot when joined channel
        raw_msg - raw IRC msg
        """
        pass

    def on_pubmsg(self, **kwargs):
        """
        called by bot when public msg received
        raw_msg - raw IRC msg
        source  - pubmsg source
        msg     - full message
        """
        pass

    def on_kick(self, **kwargs):
        """
        called by bot when somebody got kicked
        raw_msg - raw IRC msg
        who     - person who gets kicked
        source  - kicker's source
        """
        pass

    def on_me_kicked(self, **kwargs):
        """
        called by bot when kicked from channel
        raw_msg - raw IRC msg
        source  - kicker's source
        """
        pass

    def on_privmsg(self, **kwargs):
        """
        called by bot when private msg received
        raw_msg - raw IRC msg
        msg     - full message
        source  - primsg source
        """
        pass

    # see https://www.alien.net.au/irc/irc2numerics.html
    # for deep explanation
    def on_whoisuser(self, **kwargs):
        """
        called by bot when /whois response received
        raw_msg - raw IRC msg
        nick    - requested nickname
        user    - requested username
        host    - requested hostname
        """
        pass

    def on_nicknameinuse(self, **kwargs):
        """
        called by bot when given nickname is reserved
        raw_msg       - raw IRC msg
        busy_nickname - nickname bot was trying to use
        """
        pass

    def on_nick(self, **kwargs):
        """
        called by bot when somebody changes nickname
        raw_msg      - raw IRC msg
        source       - changer's source (with old nickname!)
        old_nickname - old nickname
        new_nickname - new nickname
        """

    def on_part(self, **kwargs):
        """
        called by bot when somebody lefts channel
        raw_msg - raw IRC msg
        source  - source of left user
        """

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
            self.bot.say('internal error, sorry :(')
            if self.bot.is_debug_mode_enabled(): raise

    command_impl.__command = True
    return command_impl


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

    return admin_impl
