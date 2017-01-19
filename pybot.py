import inspect
import logging
import re
import sys
import irc.bot
import irc.strings
import irc.connection
import irc.client
import plugin
import msg_parser


class pybot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, password=None):
        self.logger = logging.getLogger(__name__)
        self.plugins = []
        self.commands = {}  # map command -> func
        self.load_plugins()

        self.channel = channel
        self.server = server
        self.port = port
        self.password = password
        self.__nickname = nickname

        self.logger.debug('initiating irc.bot.SingleServerIRCBot...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.logger.debug('irc.bot.SingleServerIRCBot initiated')

    def start(self):
        self.logger.info('connecting to %s:%d...' %
                         (self.server, self.port))

        self.connection.buffer_class.errors = 'replace'
        super(pybot, self).start()

    def on_nicknameinuse(self, connection, raw_msg):
        """ called by super() when given nickname is reserved """
        self.call_plugins_methods(connection, raw_msg, 'on_nicknameinuse')
        new_nickname = self.__nickname + '_'
        self.logger.warn('nickname %s busy, using %s' % (self.__nickname, new_nickname))
        self.__nickname = new_nickname
        connection.nick(new_nickname)

    def on_welcome(self, connection, raw_msg):
        """ called by super() when connected to server """
        self.call_plugins_methods(connection, raw_msg, 'on_welcome')
        self.logger.info('connected to %s:%d using nickname %s' % (self.server, self.port, connection.get_nickname()))
        self.login(connection)
        self.join_channel(connection)

    def on_join(self, connection, raw_msg):
        """ called by super() when somebody joins channel """
        if raw_msg.source.nick == connection.get_nickname():
            self.logger.info('joined to %s' % self.channel)
            self.whois(connection.get_nickname())
        else:
            self.call_plugins_methods(connection, raw_msg, 'on_join')

    def on_privmsg(self, connection, raw_msg):
        """ called by super() when private msg received """
        self.call_plugins_methods(connection, raw_msg, 'on_privmsg')
        full_msg = raw_msg.arguments[0]
        sender_nick = raw_msg.source.nick
        print('[PRIV]>%s: %s' % (sender_nick, full_msg))

    def on_pubmsg(self, connection, raw_msg):
        """ called by super() when msg received """
        self.call_plugins_methods(connection, raw_msg, 'on_pubmsg')
        full_msg = raw_msg.arguments[0]
        sender_nick = raw_msg.source.nick

        cmd = msg_parser.split_msg_raw(msg_parser.trim_msg(self.get_command_prefix(), full_msg))
        if len(cmd) > 0 and cmd[0] in self.commands:
            func = self.commands[cmd[0]]
            func(sender_nick, cmd[1:])

    def on_kick(self, connection, raw_msg):
        self.call_plugins_methods(connection, raw_msg, 'on_kick')
        if raw_msg.arguments[0] != connection.get_nickname(): return

        self.logger.warning('kicked by %s' % raw_msg.source.nick)

        i = None
        while i != 'Y' and i != 'y' and i != 'N' and i != 'n':
            print('rejoin to %s? [Y/n]' % self.channel, end=' ')
            i = input()

        if i == 'Y' or i == 'y':
            self.join_channel(connection)
        else:
            self.die()

    def on_whoisuser(self, connection, raw_msg):
        # workaround here:
        # /whois me triggers on_me_joined call because when first time on self.on_join (== when bot joins channel) users-list is not updated yet
        if raw_msg.arguments[0] == connection.get_nickname():
            self.call_plugins_methods(connection, raw_msg, 'on_me_joined')

        self.call_plugins_methods(connection, raw_msg, 'on_whoisuser')

    def call_plugins_methods(self, connection, raw_msg, func_name):
        for p in self.get_plugins():
            try:
                p.__getattribute__(func_name)(connection, raw_msg)
            except Exception as e:
                self.logger.warn('exception caught calling %s: %s' % (func_name, e))

    def register_plugin(self, plugin_instance):
        self.plugins.append(plugin_instance)
        self.logger.info('plugin %s loaded' % type(plugin_instance).__name__)

    def register_commands_for_plugin(self, plugin_instance):
        for f in inspect.getmembers(plugin_instance, predicate=inspect.ismethod):
            func = f[1]
            func_name = f[0]
            if hasattr(func, '__command'):
                self.commands[func_name] = func
                self.logger.debug('command %s registered' % func_name)

    def load_plugins(self):
        self.logger.debug('loading plugins...')
        for plugin_class in plugin.plugin.__subclasses__():
            plugin_instance = plugin_class(self)
            self.register_plugin(plugin_instance)
            self.register_commands_for_plugin(plugin_instance)

        self.logger.debug('plugins loaded')

    def get_commands_by_plugin(self):
        """
        :return: dict {plugin_name1: [command1, command2], plugin_name2: [command3, command4], ...}
        """
        result = {}
        for plugin_name in self.get_plugins_names():
            result[plugin_name] = self.get_plugin_commands(plugin_name)

        return result

    def get_plugin_commands(self, plugin_name):
        """
        :return: commands registered by plugin plugin_name
        """
        if plugin_name in self.get_plugins_names():
            return [x for x in self.commands if type(self.commands[x].__self__).__name__ == plugin_name]
        else:
            raise Exception('no such plugin [%s]' % plugin_name)

    def get_plugins_names(self):
        """
        :return: names of registered plugins
        """
        return [type(p).__name__ for p in self.get_plugins()]

    def get_plugins(self):
        return self.plugins

    def whois(self, targets):
        """send a WHOIS command."""
        self.connection.whois(targets)

    def send_response_to_channel(self, msg):
        self.logger.debug('sending reply: %s' % msg)
        self.connection.privmsg(self.channel, msg)

    def login(self, connection):
        # TODO add more login ways
        if self.password is not None:
            connection.privmsg('NickServ', 'identify %s %s' % (self.connection.get_nickname(), self.password))

    def get_command_prefix(self):
        return '.'

    def join_channel(self, connection):
        self.logger.info('joining %s...' % self.channel)
        connection.join(self.channel)


pybot.ops = {'pingwindyktator'}
