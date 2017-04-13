import main
from unittest import mock
from irc.bot import ExponentialBackoff, missing
from collections import namedtuple


class buffer_class_t:
    def __init__(self):
        self.errors = ''


class connection_t:
    def __init__(self, bot_nickname, handlers):
        self.buffer_class = buffer_class_t()
        self.bot_nickname = bot_nickname
        self.handlers = handlers

    def privmsg(self, target, text):
        print('< ' + text)

    def get_nickname(self):
        return self.bot_nickname

    def join(self, channel):
        pass

    def whois(self, target):
        raw_msg = raw_msg_t(msg, 'pingwindyktator', 'host_pingwina')

    def nick(self, new_nickname):
        self.bot_nickname = new_nickname

    def kick(self, channel, nick, comment=""):
        print('> %s has kicked %s (%s)' % (self.get_nickname(), nick, comment))


class source_t:
    def __init__(self, nick, host):
        self.nick = nick
        self.host = host


class raw_msg_t:
    def __init__(self, full_msg, source_nick, host):
        self.source = source_t(source_nick, host)
        self.arguments = (full_msg,)


class chobj_t:
    def users(self):
        return list(set(['user1', 'user2', 'user3'] + self.opers() + self.voiced()))

    def voiced(self):
        return list(set(['voiced1', 'voiced2', 'voiced3'] + self.opers()))

    def opers(self):
        return ['op1', 'op2', 'op3']


class SingleServerIRCBot_mock:
    def __init__(self, server_list, nickname, realname,
                 reconnection_interval=missing,
                 recon=ExponentialBackoff(), **connect_params):

        self.handlers = {}
        self.channels = {}
        for method_name in ["on_nicknameinuse", "on_welcome", "on_join", "on_privmsg", "on_pubmsg", "on_kick",
                            "on_whoisuser"]:
            self.handlers[method_name] = getattr(self, method_name)

        self.channels[getattr(self, 'channel')] = chobj_t()
        self.connection = connection_t(nickname, self.handlers)

    def call_handler(self, handler_name, *args):
        if not handler_name in self.handlers: return
        self.handlers[handler_name](*args)

    def start(self):
        while True:
            msg = input('> ')
            if not msg: continue
            raw_msg = raw_msg_t(msg, 'pingwindyktator', 'host_pingwina')
            self.call_handler('on_pubmsg', self.connection, raw_msg)

    def disconnect(self, msg):
        print('> %s has quit (%s)' % (self.connection.get_nickname(), msg))

    def die(self, msg):
        self.disconnect(msg)
        exit(0)


def simulator_main():
    patcher = mock.patch.object(main.pybot, '__bases__', (SingleServerIRCBot_mock,))
    with patcher:
        patcher.is_local = True
        main.main()


if __name__ == "__main__":
    simulator_main()