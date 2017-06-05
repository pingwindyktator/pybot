import inspect
import logging
import ssl
import time
import textwrap
import sys
import plugin
import msg_parser
import irc.bot
import irc.connection

from queue import Queue
from threading import Thread
from functools import total_ordering
from color import color
from fuzzywuzzy import process
from fuzzywuzzy import fuzz


@total_ordering
class irc_nickname(str):
    def __eq__(self, other):
        return self.casefold() == other.casefold()

    def __lt__(self, other):
        return self.casefold() < other.casefold()

    def __hash__(self):
        return hash(self.casefold())


# noinspection PyUnusedLocal
class pybot(irc.bot.SingleServerIRCBot):
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)

        if config['colors']:
            color.enable_colors()
            self.logger.debug('colors loaded')
        else:
            color.disable_colors()
            self.logger.debug('colors loaded')

        self.logger.debug('initiating irc.bot.SingleServerIRCBot...')
        connection_args = {}
        if config['use_ssl']:
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            connection_args['connect_factory'] = ssl_factory

        super(pybot, self).__init__([(config['server'], config['port'])], config['nickname'][0], config['nickname'][0], **connection_args)
        self.logger.debug('irc.bot.SingleServerIRCBot initiated')

        self._nickname_id = 0
        self.config = config
        self._joined_to_channel = False
        self._autorejoin_attempts = 0
        self.channel = None

        self.plugins = set()
        self.commands = {}  # command -> func
        self.msg_regexes = {}  # regex -> [funcs]
        self._say_queue = Queue()
        self._say_thread = None
        self._load_plugins()

    class _say_info:
        def __init__(self, target, msg):
            self.target = target
            self.msg = msg

    def start(self):
        self._joined_to_channel = False
        ssl_info = ' over SSL' if self.config['use_ssl'] else ''
        self.logger.info(f'connecting to {self.config["server"]}:{self.config["port"]}{ssl_info}...')
        self.connection.buffer_class.errors = 'replace'
        super(pybot, self).start()

    # callbacks

    def on_nicknameinuse(self, connection, raw_msg):
        """ called by super() when given nickname is reserved """
        nickname = irc_nickname(self.config['nickname'][self._nickname_id])
        self._nickname_id += 1

        if self._nickname_id >= len(self.config['nickname']):
            self.logger.critical(f'nickname {nickname} is busy, no more nicknames to use')
            sys.exit(2)

        new_nickname = irc_nickname(self.config['nickname'][self._nickname_id])
        self.logger.warning(f'nickname {nickname} is busy, using {new_nickname}')
        self._call_plugins_methods('on_nicknameinuse', raw_msg=raw_msg, busy_nickname=nickname)
        self.connection.nick(new_nickname)
        self.login()

    def on_welcome(self, connection, raw_msg):
        """ called by super() when connected to server """
        ssl_info = ' over SSL' if self.config['use_ssl'] else ''
        self.logger.info(f'connected to {self.config["server"]}:{self.config["port"]}{ssl_info} using nickname {self.get_nickname()}')
        self._call_plugins_methods('on_welcome', raw_msg=raw_msg, server=self.config['server'], port=self.config['port'], nickname=self.get_nickname())
        self.login()
        self.join_channel()

    def on_disconnect(self, connection, raw_msg):
        """ called by super() when disconnected to server """
        self.logger.warning(f'disconnected from {self.config["server"]}: {raw_msg.arguments[0] if raw_msg.arguments else ""}')
        self._call_plugins_methods('on_disconnect', raw_msg=raw_msg, server=self.config['server'], port=self.config['port'])

    def on_join(self, connection, raw_msg):
        """ called by super() when somebody joins channel """
        if raw_msg.source.nick == self.get_nickname():
            self.logger.info(f'joined to {self.config["channel"]}')
            self.whois(self.get_nickname())
        else:
            self._call_plugins_methods('on_join', raw_msg=raw_msg, source=raw_msg.source)

    def on_privmsg(self, connection, raw_msg):
        """ called by super() when private msg received """
        full_msg = raw_msg.arguments[0]
        sender_nick = irc_nickname(raw_msg.source.nick)
        logging.info(f'[PRIVATE MSG] {sender_nick}: {full_msg}')

        if self.is_user_ignored(sender_nick):
            self.logger.debug(f'user {sender_nick} is ignored, skipping msg')
            return

        self._call_plugins_methods('on_privmsg', raw_msg=raw_msg, source=raw_msg.source, msg=full_msg)

    def on_pubmsg(self, connection, raw_msg):
        """ called by super() when msg received """
        full_msg = raw_msg.arguments[0].strip()
        sender_nick = irc_nickname(raw_msg.source.nick)

        if self.is_user_ignored(sender_nick):
            self.logger.debug(f'user {sender_nick} is ignored, skipping msg')
            return

        self._call_plugins_methods('on_pubmsg', raw_msg=raw_msg, source=raw_msg.source, msg=full_msg)

        raw_cmd = msg_parser.trim_msg(self.config['command_prefix'], full_msg)
        if not raw_cmd:
            raw_cmd = msg_parser.trim_msg(self.get_nickname() + ':', full_msg)
        if not raw_cmd:
            raw_cmd = msg_parser.trim_msg(self.get_nickname() + ',', full_msg)

        args_list = raw_cmd.split()
        cmd = args_list[0] if len(args_list) > 0 else ''
        args_list = args_list[1:]
        assert raw_cmd.startswith(cmd)
        raw_cmd = raw_cmd[len(cmd):].strip()

        if cmd in self.commands:
            func = self.commands[cmd]
            self.logger.debug(f'calling command  {func.__qualname__}(sender_nick={sender_nick}, args={args_list}, msg=\'{raw_cmd}\', raw_msg=...)...')
            func(sender_nick=sender_nick, args=args_list, msg=raw_cmd, raw_msg=raw_msg)
        elif self.config['try_autocorrect'] and cmd:
            possible_cmd = self._get_best_command_match(cmd)
            if possible_cmd:
                self.say(f"no such command: {cmd}, did you meant '{possible_cmd}'?")
            else:
                self.say(f'no such command: {cmd}')

        for reg in self.msg_regexes:
            regex_search_result = reg.findall(full_msg)
            if regex_search_result:
                for func in self.msg_regexes[reg]:
                    self.logger.debug(f'calling message regex handler  {func.__qualname__}(sender_nick={sender_nick}, msg=\'{full_msg}\', reg_res={regex_search_result}, raw_msg=...)...')
                    func(sender_nick=sender_nick, msg=full_msg, reg_res=regex_search_result, raw_msg=raw_msg)

    def on_kick(self, connection, raw_msg):
        """ called by super() when somebody gets kicked """
        if raw_msg.arguments[0] == self.get_nickname():
            self.on_me_kicked(self.connection, raw_msg)
        else:
            self._call_plugins_methods('on_kick', raw_msg=raw_msg, who=raw_msg.arguments[0], source=raw_msg.source)

    def on_me_kicked(self, connection, raw_msg):
        """ called when bot gets kicked """
        self.logger.warning(f'kicked by {raw_msg.source.nick}')
        self._call_plugins_methods('on_me_kicked', raw_msg=raw_msg, source=raw_msg.source)
        self._joined_to_channel = False

        if self._autorejoin_attempts >= self.config['max_autorejoin_attempts']:
            self.logger.warning('autorejoin attempts limit reached, waiting for user interact now')
            choice = None
            while choice != 'Y' and choice != 'y' and choice != 'N' and choice != 'n':
                choice = input(f'rejoin to {self.config["channel"]}? [Y/n] ')

            if choice == 'Y' or choice == 'y':
                self._autorejoin_attempts = 0
                self.join_channel()
            else:
                self.die()
        else:
            self._autorejoin_attempts += 1
            self.join_channel()

    def on_whoisuser(self, connection, raw_msg):
        """ called by super() when WHOIS response arrives """
        # workaround here:
        # /whois me triggers on_me_joined call because when first time on self.on_join (== when bot joins channel) users-list is not updated yet
        if raw_msg.arguments[0] == self.get_nickname() and not self._joined_to_channel:
            self.on_me_joined(connection, raw_msg)

        self._call_plugins_methods('on_whoisuser', raw_msg=raw_msg, nick=irc_nickname(raw_msg.arguments[0]), user=raw_msg.arguments[1], host=raw_msg.arguments[2])

    def on_me_joined(self, connection, raw_msg):
        """ called when bot joins channel """
        self._joined_to_channel = True
        self.channel = self.channels[self.config['channel']]
        self._call_plugins_methods('on_me_joined', raw_msg=raw_msg)

    def on_nick(self, connection, raw_msg):
        """ called by super() when somebody changes nickname """
        self._call_plugins_methods('on_nick', raw_msg=raw_msg, source=raw_msg.source, old_nickname=irc_nickname(raw_msg.source.nick), new_nickname=irc_nickname(raw_msg.target))

    def on_part(self, connection, raw_msg):
        """ called by super() when somebody lefts channel """
        self._call_plugins_methods('on_part', raw_msg=raw_msg, source=raw_msg.source)

    def on_quit(self, connection, raw_msg):
        """ called by super() when somebody disconnects from IRC server """
        self._call_plugins_methods('on_quit', raw_msg=raw_msg, source=raw_msg.source)

    def on_ctcp(self, connection, raw_msg):
        """ called by super() when ctcp arrives (/me ...) """
        self._call_plugins_methods('on_ctcp', raw_msg=raw_msg, source=raw_msg.source, msg=raw_msg.arguments[1] if len(raw_msg.arguments) > 1 else '')

    def login(self):
        # TODO add more login ways
        # TODO plugin
        if 'password' in self.config and self._nickname_id < len(self.config['password']):
            password = self.config['password'][self._nickname_id]
            self.say('NickServ', f"identify {self.get_nickname()} {password}")
            if password is not None and password != '':
                self.logger.info(f'identifying as {self.get_nickname()}...')

    # don't touch this

    def _get_best_command_match(self, command):
        choices = [c.replace('_', ' ') for c in self.commands]
        command = command.replace('_', ' ')
        result = process.extract(command, choices, scorer=fuzz.token_sort_ratio)
        result = [(r[0].replace(' ', '_'), r[1]) for r in result]
        return result[0][0] if result[0][1] > 65 else None

    def _call_plugins_methods(self, func_name, **kwargs):
        for p in self.get_plugins():
            try:
                p.__getattribute__(func_name)(**kwargs)
            except Exception as e:
                self.logger.error(f'exception caught calling {p.__getattribute__(func_name).__qualname__}: {e}')
                if self.is_debug_mode_enabled(): raise

    def _load_plugins(self):
        self.logger.debug('loading plugins...')
        disabled_plugins = self.config['disabled_plugins'] if 'disabled_plugins' in self.config else []
        enabled_plugins = self.config['enabled_plugins'] if 'enabled_plugins' in self.config else [x.__name__ for x in plugin.plugin.__subclasses__()]

        for plugin_class in plugin.plugin.__subclasses__():
            if plugin_class.__name__ in disabled_plugins or plugin_class.__name__ not in enabled_plugins:
                self.logger.info(f'- plugin {plugin_class.__name__} skipped')
                continue

            try:
                plugin_instance = plugin_class(self)
            except Exception as e:
                self.logger.warning(f'- unable to load plugin {plugin_class.__name__}: {e}')
                continue

            self.register_plugin(plugin_instance)

        self.logger.debug('plugins loaded')

    def _say_dispatcher(self, msg, target):
        if self.config['flood_protection']:
            self._say_queue.put(self._say_info(target, msg))

            if self._say_thread is None or not self._say_thread.is_alive():
                self.logger.debug('starting _say_thread...')
                self._say_thread = Thread(target=self._process_say)
                self._say_thread.start()
        else:
            self._say_impl(msg, target)

    def _say_impl(self, msg, target):
        try:
            self.connection.privmsg(target, msg)
        except Exception as e:
            self.logger.error(f'cannot send "{msg}": {e}. discarding msg...')

    def _process_say(self):
        msgs_sent = 0

        while not self._say_queue.empty() and msgs_sent < 5:
            say_info = self._say_queue.get()
            self.logger.debug(f'sending reply to {say_info.target}: {say_info.msg}')
            self._say_impl(say_info.msg, say_info.target)
            msgs_sent += 1
            self._say_queue.task_done()

        time.sleep(0.5)  # to not get kicked because of Excess Flood

        while not self._say_queue.empty():
            say_info = self._say_queue.get()
            self.logger.debug(f'sending reply to {say_info.target}: {say_info.msg}')
            self._say_impl(say_info.msg, say_info.target)
            time.sleep(0.5)  # to not get kicked because of Excess Flood

        self.logger.debug('no more msgs to send, exiting...')

    def _register_plugin_handlers(self, plugin_instance):
        if plugin_instance not in self.plugins:
            self.logger.error(f'plugin {type(plugin_instance).__name__} not registered, aborting...')
            raise RuntimeError(f'plugin {type(plugin_instance).__name__} not registered!')

        for f in inspect.getmembers(plugin_instance, predicate=inspect.ismethod):
            func = f[1]
            func_name = f[0]
            if hasattr(func, '__command'):
                if func_name in self.commands:
                    self.logger.warning(f'command {func_name} already registered, skipping...')
                    continue

                self.commands[func_name] = func
                self.logger.debug(f'command {func_name} registered')

            if hasattr(func, '__regex'):
                __regex = getattr(func, '__regex')
                if __regex not in self.msg_regexes:
                    self.msg_regexes[__regex] = []

                self.msg_regexes[__regex].append(func)
                self.msg_regexes[__regex] = list(set(self.msg_regexes[__regex]))
                self.logger.debug(f'regex for {func.__qualname__} registered: \'{getattr(func, "__regex").pattern}\'')

    # API funcs

    def register_plugin(self, plugin_instance):
        if not issubclass(type(plugin_instance), plugin.plugin):
            self.logger.error(f'trying to register no-plugin class {type(plugin_instance).__name__} as plugin, aborting...')
            raise RuntimeError(f'class {type(plugin_instance).__name__} does not inherit from plugin!')

        if plugin_instance in self.plugins:
            self.logger.warning(f'plugin {type(plugin_instance).__name__} already registered, skipping...')
            return

        self.plugins.add(plugin_instance)
        self.logger.info(f'+ plugin {type(plugin_instance).__name__} loaded')
        self._register_plugin_handlers(plugin_instance)

    def get_commands_by_plugin(self):
        """
        :return: dict {plugin_name1: [command1, command2, ...], plugin_name2: [command3, command4, ...], ...}
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

    def get_plugins(self):
        return self.plugins

    def get_plugins_names(self):
        """
        :return: names of registered plugins
        """
        return [type(p).__name__ for p in self.get_plugins()]

    def whois(self, targets):
        """ send a WHOIS command """
        self.connection.whois(targets)

    def say(self, msg, target=None):
        if not target: target = self.config['channel']

        if self.is_msg_too_long(msg):
            self.logger.debug('privmsg too long, wrapping...')
            for part in textwrap.wrap(msg, 450):
                self._say_dispatcher(part, target)
        else:
            self._say_dispatcher(msg, target)

    def notice(self, msg, target):
        self.connection.notice(target, msg)

    def is_user_ignored(self, nickname):
        nickname = irc_nickname(nickname)
        return ('ignored_users' in self.config and nickname in self.config['ignored_users']) and (nickname not in self.config['ops'])

    @staticmethod
    def is_msg_too_long(msg):
        encoded_msg = msg.encode('utf-8')
        return len(encoded_msg + b'\r\n') > 512  # max msg len defined by IRC protocol

    def join_channel(self):
        self.logger.info(f'joining {self.config["channel"]}...')
        self.connection.join(self.config['channel'])

    def leave_channel(self):
        self.logger.info(f'leaving {self.config["channel"]}...')
        self.connection.part(self.config['channel'])

    def is_debug_mode_enabled(self):
        return 'debug' in self.config and self.config['debug']

    def get_nickname(self):
        return irc_nickname(self.connection.get_nickname())
