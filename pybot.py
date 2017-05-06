import inspect
import logging
import ssl
import textwrap
import sys
import plugin
import msg_parser
import irc.bot
import irc.connection


# noinspection PyUnusedLocal
class pybot(irc.bot.SingleServerIRCBot):
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)

        self.logger.debug('initiating irc.bot.SingleServerIRCBot...')
        connection_args = {}
        if config['use_ssl']:
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            connection_args['connect_factory'] = ssl_factory

        super(pybot, self).__init__([(config['server'], config['port'])], config['nickname'][0], config['nickname'][0], **connection_args)
        self.logger.debug('irc.bot.SingleServerIRCBot initiated')

        self.nickname_id = 0
        self.config = config
        self.joined_to_channel = False
        self.autorejoin_attempts = 0

        self.plugins = set()
        self.commands = {}  # map command -> func
        self.load_plugins()

    def start(self):
        ssl_info = ' over SSL' if self.config['use_ssl'] else ''
        self.logger.info('connecting to %s:%d%s...' % (self.config['server'], self.config['port'], ssl_info))

        self.connection.buffer_class.errors = 'replace'
        super(pybot, self).start()

    def on_nicknameinuse(self, connection, raw_msg):
        """ called by super() when given nickname is reserved """
        nickname = self.config['nickname'][self.nickname_id]
        self.nickname_id += 1

        if self.nickname_id >= len(self.config['nickname']):
            self.logger.critical('nickname %s is busy, no more nicknames to use' % nickname)
            sys.exit(2)

        new_nickname = self.config['nickname'][self.nickname_id]
        self.logger.warning('nickname %s is busy, using %s' % (nickname, new_nickname))
        self.call_plugins_methods('on_nicknameinuse', raw_msg=raw_msg, busy_nickname=nickname)
        self.connection.nick(new_nickname)
        self.login()

    def on_welcome(self, connection, raw_msg):
        """ called by super() when connected to server """
        ssl_info = ' over SSL' if self.config['use_ssl'] else ''
        self.logger.info('connected to %s:%d%s using nickname %s' % (self.config['server'], self.config['port'], ssl_info, self.connection.get_nickname()))
        self.call_plugins_methods('on_welcome', raw_msg=raw_msg, server=self.config['server'], port=self.config['port'], nickname=self.connection.get_nickname())
        self.login()
        self.join_channel()

    def on_disconnect(self, connection, raw_msg):
        """ called by super() when disconnected to server """
        self.call_plugins_methods('on_disconnect', raw_msg=raw_msg, server=self.config['server'], port=self.config['port'])

    def on_join(self, connection, raw_msg):
        """ called by super() when somebody joins channel """
        if raw_msg.source.nick == self.connection.get_nickname():
            self.logger.info('joined to %s' % self.config['channel'])
            self.whois(self.connection.get_nickname())
        else:
            self.call_plugins_methods('on_join', raw_msg=raw_msg, source=raw_msg.source)

    def on_privmsg(self, connection, raw_msg):
        """ called by super() when private msg received """
        full_msg = raw_msg.arguments[0]
        sender_nick = raw_msg.source.nick
        logging.info('[PRIV] %s: %s' % (sender_nick, full_msg))
        self.call_plugins_methods('on_privmsg', raw_msg=raw_msg, msg=full_msg, source=raw_msg.source)

    def on_pubmsg(self, connection, raw_msg):
        """ called by super() when msg received """
        full_msg = raw_msg.arguments[0].strip()
        sender_nick = raw_msg.source.nick.lower()
        self.call_plugins_methods('on_pubmsg', raw_msg=raw_msg, source=raw_msg.source, msg=full_msg)

        raw_cmd = msg_parser.trim_msg(self.get_command_prefix(), full_msg)
        cmd_list = raw_cmd.split()
        cmd = cmd_list[0] if len(cmd_list) > 0 else ''
        cmd_list = cmd_list[1:]
        assert raw_cmd.startswith(cmd)
        raw_cmd = raw_cmd[len(cmd):].strip()

        if cmd in self.commands:
            func = self.commands[cmd]
            func(sender_nick=sender_nick, args=cmd_list, msg=raw_cmd, raw_msg=raw_msg)

    def on_kick(self, connection, raw_msg):
        if raw_msg.arguments[0] == self.connection.get_nickname():
            self.on_me_kicked(self.connection, raw_msg)
        else:
            self.call_plugins_methods('on_kick', raw_msg=raw_msg, who=raw_msg.arguments[0], source=raw_msg.source)

    def on_me_kicked(self, connection, raw_msg):
        self.logger.warning('kicked by %s' % raw_msg.source.nick)
        self.call_plugins_methods('on_me_kicked', raw_msg=raw_msg, source=raw_msg.source)
        self.joined_to_channel = False

        if self.autorejoin_attempts >= self.config['max_autorejoin_attempts']:
            self.logger.warning('autorejoin attempts limit reached, waiting for user interact now')
            choice = None
            while choice != 'Y' and choice != 'y' and choice != 'N' and choice != 'n':
                choice = input('rejoin to %s? [Y/n] ' % self.config['channel'])

            if choice == 'Y' or choice == 'y':
                self.autorejoin_attempts = 0
                self.join_channel()
            else:
                self.die()
        else:
            self.autorejoin_attempts += 1
            self.join_channel()

    def on_whoisuser(self, connection, raw_msg):
        # workaround here:
        # /whois me triggers on_me_joined call because when first time on self.on_join (== when bot joins channel) users-list is not updated yet
        if raw_msg.arguments[0] == self.connection.get_nickname() and not self.joined_to_channel:
            self.call_plugins_methods('on_me_joined', raw_msg=raw_msg, channel=self.config['channel'])
            self.joined_to_channel = True

        self.call_plugins_methods('on_whoisuser', raw_msg=raw_msg, nick=raw_msg.arguments[0], user=raw_msg.arguments[1], host=raw_msg.arguments[2])

    def call_plugins_methods(self, func_name, *args, **kwargs):
        for p in self.get_plugins():
            try:
                p.__getattribute__(func_name)(*args, **kwargs)
            except Exception as e:
                self.logger.error('exception caught calling %s: %s' % (p.__getattribute__(func_name), e))

    def register_plugin(self, plugin_instance):
        self.plugins.add(plugin_instance)
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
        disabled_plugins = self.config['disabled_plugins'] if 'disabled_plugins' in self.config else []
        enabled_plugins = self.config['enabled_plugins'] if 'enabled_plugins' in self.config else [x.__name__ for x in plugin.plugin.__subclasses__()]

        for plugin_class in plugin.plugin.__subclasses__():
            if plugin_class.__name__ in disabled_plugins or plugin_class.__name__ not in enabled_plugins:
                self.logger.info('skipping %s plugin' % plugin_class.__name__)
                continue

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
            return None

    def get_plugins_names(self):
        """
        :return: names of registered plugins
        """
        return [type(p).__name__ for p in self.get_plugins()]

    def get_plugins(self):
        return self.plugins

    def whois(self, targets):
        """ send a WHOIS command """
        self.connection.whois(targets)

    def say(self, msg, target=None):
        if not target: target = self.config['channel']
        self.logger.debug('sending reply to %s: %s' % (target, msg))

        if self.is_msg_too_long(msg):
            self.logger.debug('privmsg too long, wrapping...')
            for part in textwrap.wrap(msg, 450):
                self.say(part, target)
        else:
            self.connection.privmsg(target, msg)

    @staticmethod
    def is_msg_too_long(msg):
        encoded_msg = msg.encode('utf-8')
        return len(encoded_msg + b'\r\n') > 512  # max msg len defined by IRC protocol

    def login(self):
        # TODO add more login ways
        # TODO plugin
        if self.config['password'] is not None and self.nickname_id < len(self.config['password']):
            password = self.config['password'][self.nickname_id]
            if password is not None and password != '':
                self.logger.info('identifying as %s...' % self.connection.get_nickname())
                self.say('NickServ', 'identify %s %s' % (self.connection.get_nickname(), password))

    def get_command_prefix(self):
        return '.'

    def join_channel(self):
        self.logger.info('joining %s...' % self.config['channel'])
        self.connection.join(self.config['channel'])

    def leave_channel(self):
        self.logger.info('leaving %s...' % self.config['channel'])
        self.connection.part(self.config['channel'])
