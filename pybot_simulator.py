import sys
import _main
import logging

from unittest import mock
from irc.bot import ExponentialBackoff, missing
from color import color


class raw_msg_builder:
    @staticmethod
    def build_for_on_whoisuser(nick, user, host):
        return raw_msg_t(nick, user, host, (nick, user, host,))

    @staticmethod
    def build_for_on_whoisuser_on_nick(nick):
        return raw_msg_t(nick, nick + '_user', nick + '_host', (nick, nick.lower() + '_user', nick.lower() + '_host',))

    @staticmethod
    def build_for_on_pubmsg(nick, user, host, msg):
        return raw_msg_t(nick, user, host, (msg,))

    @staticmethod
    def build_for_on_pubmsg_on_nick(nick, msg):
        return raw_msg_t(nick, nick.lower() + '_user', nick.lower() + '_host', (msg,))

    @staticmethod
    def build_for_on_join(nick, user, host):
        return raw_msg_t(nick, user, host, ())

    @staticmethod
    def build_for_on_on_join_on_nick(nick):
        return raw_msg_t(nick, nick.lower() + '_user', nick.lower() + '_host', ())


class buffer_class_t:
    def __init__(self):
        self.errors = ''


class connection_t:
    def __init__(self, bot_nickname, handlers):
        self.buffer_class = buffer_class_t()
        self.bot_nickname = bot_nickname
        self.handlers = handlers

    def call_handler(self, handler_name, *args):
        if handler_name not in self.handlers: return
        self.handlers[handler_name](*args)

    def privmsg(self, target, text):
        print('< ' + text)

    def get_nickname(self):
        return self.bot_nickname

    def join(self, channel):
        pass

    def whois(self, target):
        raw_msg = raw_msg_builder.build_for_on_whoisuser_on_nick(target)
        self.call_handler('on_whoisuser', self, raw_msg)

    def nick(self, new_nickname):
        self.bot_nickname = new_nickname

    def kick(self, channel, nick, comment=''):
        print(f'> {self.get_nickname()} has kicked {nick} ({comment})')


class source_t:
    def __init__(self, nick, user, host):
        self.nick = nick
        self.host = host
        self.user = user


class raw_msg_t:
    def __init__(self, source_nick, user, host, arguments):
        self.source = source_t(source_nick, user, host)
        self.arguments = arguments


class chobj_t:
    def __init__(self, bot_nickname):
        self.bot_nickname = bot_nickname

    def users(self):
        return list(set(['user1', 'user2', 'user3'] + self.opers() + self.voiced() + [self.bot_nickname]))

    def voiced(self):
        return list(set(['voiced1', 'voiced2', 'voiced3'] + self.opers()))

    def opers(self):
        return ['op1', 'op2', 'op3', 'pingwindyktator']


class SingleServerIRCBot_mock:
    def __init__(self, server_list, nickname, realname,
                 reconnection_interval=missing,
                 recon=ExponentialBackoff(), **connect_params):

        handlers = {}
        self.channels = {}
        for method_name in ["on_nicknameinuse", "on_welcome", "on_join", "on_privmsg", "on_pubmsg", "on_kick",
                            "on_whoisuser"]:
            handlers[method_name] = getattr(self, method_name)

        self.connection = connection_t(nickname, handlers)

    def init_bot(self):
        self.connection.call_handler('on_welcome', self.connection, None)

        raw_msg = raw_msg_builder.build_for_on_on_join_on_nick(self.connection.get_nickname())
        self.connection.call_handler('on_join', self.connection, raw_msg)

    def start(self):
        self.channels[getattr(self, 'config')['channel']] = chobj_t(self.connection.get_nickname())
        self.init_bot()

        while True:
            msg = input('> ')
            if not msg: continue
            raw_msg = raw_msg_builder.build_for_on_pubmsg_on_nick('pingwindyktator', msg)
            self.connection.call_handler('on_pubmsg', self.connection, raw_msg)

    def disconnect(self, msg):
        print(f'> {self.connection.get_nickname()} has quit ({msg})')

    def die(self, msg):
        self.disconnect(msg)
        exit(0)


def configure_logger(*args, **kwargs):
    logging_format = '%(levelname)-10s%(asctime)s %(filename)s:%(funcName)-16s: %(message)s'
    logging.basicConfig(format=logging_format, level=logging.INFO, stream=sys.stdout)


def simulator_main():
    _main.configure_logger = configure_logger
    color.disable_colors()
    color.enable_colors = lambda: None
        
    patcher = mock.patch.object(_main.pybot, '__bases__', (SingleServerIRCBot_mock,))
    with patcher:
        patcher.is_local = True
        _main.main()


if __name__ == "__main__":
    simulator_main()
