import inspect
import logging
import sqlite3
import ssl
import time
import textwrap
import sys
import random
import atexit
import os
import plugin
import msg_parser
import irc.bot
import irc.connection
import irc.client
import utils
import signal
import sys

from queue import Queue
from threading import Thread, Lock
from color import color
from utils import irc_nickname
from fuzzywuzzy import process, fuzz
from irc.client import MessageTooLong
from ping_ponger import ping_ponger


# noinspection PyUnusedLocal
class pybot(irc.bot.SingleServerIRCBot):
    def __init__(self, config, debug_mode=False):
        self._logger = logging.getLogger(__name__)
        self._logger.info('starting pybot...')

        self.config = config
        self._nickname_id = 0
        self._autorejoin_attempts = 0
        self._plugins = set()
        self._commands = {}  # command -> func
        self._msg_regexps = {}  # regex -> [funcs]
        self._say_queue = Queue()
        self._say_thread = None
        self._dying = False
        self._debug_mode = debug_mode
        self._fixed_command = None
        self._fixed_command_lock = Lock()

        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self._db_ops_tablename = 'ops'
        self._db_ignored_users_tablename = 'ignored_users'
        self._db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self._db_cursor = self._db_connection.cursor()
        self._db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self._db_ops_tablename}' (nickname TEXT primary key not null)")
        self._db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self._db_ignored_users_tablename}' (nickname TEXT primary key not null)")
        self._db_mutex = Lock()

        if self.config['colors']:
            color.enable_colors()
            self._logger.debug('colors loaded')
        else: color.disable_colors()

        self._logger.debug('initiating irc.bot.SingleServerIRCBot...')
        connection_args = {}
        if self.config['use_ssl']:
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            connection_args['connect_factory'] = ssl_factory

        super(pybot, self).__init__([(self.config['server'], self.config['port'])], self.config['nickname'][0], self.config['nickname'][0], **connection_args)
        self._ping_ponger = ping_ponger(self.connection, self.config['health_check_interval_s'], self.on_not_healthy) if self.config['health_check'] else utils.null_object()
        self._logger.debug('irc.bot.SingleServerIRCBot initiated')

        if not debug_mode:
            signal.signal(signal.SIGINT, self._sigint_handler)
            atexit.register(self._atexit)

        self._load_plugins()

    class _say_info:
        def __init__(self, target, msg):
            self.target = target
            self.msg = msg

    def start(self):
        ssl_info = ' over SSL' if self.config['use_ssl'] else ''
        self._logger.info(f'connecting to {self.config["server"]}:{self.config["port"]}{ssl_info}...')
        self.connection.buffer_class.errors = 'replace'
        super(pybot, self).start()

    def on_not_healthy(self):
        self._logger.warning(f'unexpectedly disconnected from {self.config["server"]}')
        self._ping_ponger.stop()
        self.start()

    # callbacks

    def on_nicknameinuse(self, _, raw_msg):
        """ called by super() when given nickname is reserved """
        old_nickname = self.config['nickname'][self._nickname_id]
        self._nickname_id += 1

        if self._nickname_id >= len(self.config['nickname']):
            self._logger.critical(f'nickname {old_nickname} is busy, no more nicknames to use')
            sys.exit(2)

        new_nickname = irc_nickname(self.config['nickname'][self._nickname_id])
        self._logger.warning(f'nickname {old_nickname} is busy, trying {new_nickname}')
        self._call_plugins_methods('nicknameinuse', raw_msg=raw_msg, busy_nickname=old_nickname)
        self.connection.nick(new_nickname)

    def on_welcome(self, _, raw_msg):
        """ called by super() when connected to server """
        self._ping_ponger.start()
        ssl_info = ' over SSL' if self.config['use_ssl'] else ''
        self._logger.info(f'connected to {self.config["server"]}:{self.config["port"]}{ssl_info} using nickname {self.get_nickname()}')
        self._call_plugins_methods('welcome', raw_msg=raw_msg, server=self.config['server'], port=self.config['port'], nickname=self.get_nickname())
        self._login()
        self.join_channel()

    def on_disconnect(self, _, raw_msg):
        """ called by super() when disconnected from server """
        self._ping_ponger.stop()
        msg = f': {raw_msg.arguments[0]}' if raw_msg.arguments else ''
        self._logger.warning(f'disconnected from {self.config["server"]}{msg}')

        if not self._dying:
            self._call_plugins_methods('disconnect', raw_msg=raw_msg, server=self.config['server'], port=self.config['port'])
            self.start()

    def on_quit(self, _, raw_msg):
        """ called by super() when somebody disconnects from IRC server """
        self._call_plugins_methods('quit', raw_msg=raw_msg, source=raw_msg.source)

    def on_join(self, _, raw_msg):
        """ called by super() when somebody joins channel """
        self.names()  # to immediately updated channel's user list
        if raw_msg.source.nick == self.get_nickname() and not self.joined_to_channel():
            self._logger.info(f'joined to {self.config["channel"]}')
            self._call_plugins_methods('me_joined', raw_msg=raw_msg)
        else:
            self._call_plugins_methods('join', raw_msg=raw_msg, source=raw_msg.source)

    def on_privmsg(self, _, raw_msg):
        """ called by super() when private msg received """
        full_msg = raw_msg.arguments[0]
        sender_nick = irc_nickname(raw_msg.source.nick)
        logging.info(f'[PRIVATE MSG] {sender_nick}: {full_msg}')

        if self.is_user_ignored(sender_nick):
            self._logger.debug(f'user {sender_nick} is ignored, skipping msg')
            return

        self._call_plugins_methods('privmsg', raw_msg=raw_msg, source=raw_msg.source, msg=full_msg)

    def on_pubmsg(self, _, raw_msg):
        """ called by super() when msg received """
        full_msg = raw_msg.arguments[0].strip()
        sender_nick = irc_nickname(raw_msg.source.nick)

        if self.is_user_ignored(sender_nick):
            self._logger.debug(f'user {sender_nick} is ignored, skipping msg')
            return

        self._call_plugins_methods('pubmsg', raw_msg=raw_msg, source=raw_msg.source, msg=full_msg)

        args = msg_parser.trim_msg(self.config['command_prefix'], full_msg)
        if not args:
            args = msg_parser.trim_msg(self.get_nickname() + ':', full_msg)
        if not args:
            args = msg_parser.trim_msg(self.get_nickname() + ',', full_msg)

        # fix should not affect msg regexps
        reg_raw_msg = raw_msg
        reg_full_msg = full_msg
        if args and args.split()[0].strip() == 'fix':
            fixed_command = self._get_fixed_command()
            if 'builtins' not in self.get_plugins_names() or 'fix' not in self.get_plugin_commands('builtins'):
                pass
            elif hasattr(self.get_commands()['fix'], '__admin') and not self.is_user_op(sender_nick):
                pass
            elif not fixed_command:
                self.say('no fix available')
                args = ''  # to disable further cmd executing
            else:
                self._logger.info(f'fixing command for {sender_nick}: {fixed_command}')
                args = fixed_command
                self.register_fixed_command(None)
                raw_msg = None
                full_msg = None

        args_list = args.split()
        cmd = args_list[0].strip() if args_list else ''
        args_list = args_list[1:]
        assert args.startswith(cmd)
        args = args[len(cmd):].strip()

        # .set entry some msg
        # cmd       == "set"
        # full_msg  == ".set entry some msg"
        # args      == "entry some msg"
        # args_list == ["some", "msg"]
        # raw_msg   == IRC Event class

        if cmd in self.get_commands():
            func = self.get_commands()[cmd]
            self._logger.debug(f'calling command  {func.__qualname__}(sender_nick={sender_nick}, args={args_list}, msg=\'{args}\', raw_msg=...)...')
            func(sender_nick=sender_nick, args=args_list, msg=args, raw_msg=raw_msg)
        elif self.config['try_autocorrect'] and cmd and len(cmd) > 0 and cmd[0].isalpha():
            possible_cmd = self._get_best_command_match(cmd, sender_nick)
            if possible_cmd:
                self.say(f"no such command: {cmd}, did you mean '{possible_cmd}'?")
                if possible_cmd != 'fix':
                    self.register_fixed_command(f'{possible_cmd} {args}')
            else:
                self.say(f'no such command: {cmd}')

        for reg in self._msg_regexps:
            regex_search_result = reg.findall(reg_full_msg)
            if regex_search_result:
                for func in self._msg_regexps[reg]:
                    self._logger.debug(f'calling message regex handler  {func.__qualname__}(sender_nick={sender_nick}, msg=\'{reg_full_msg}\', reg_res={regex_search_result}, raw_msg=...)...')
                    func(sender_nick=sender_nick, msg=reg_full_msg, reg_res=regex_search_result, raw_msg=reg_raw_msg)

    def on_kick(self, _, raw_msg):
        """ called by super() when somebody gets kicked """
        if raw_msg.arguments[0] == self.get_nickname():
            self.on_me_kicked(self.connection, raw_msg)
        else:
            self._call_plugins_methods('kick', raw_msg=raw_msg, who=raw_msg.arguments[0], source=raw_msg.source)

    def on_me_kicked(self, _, raw_msg):
        """ called when bot gets kicked """
        self._logger.warning(f'kicked by {raw_msg.source.nick}')
        self._call_plugins_methods('me_kicked', raw_msg=raw_msg, source=raw_msg.source)

        if self._autorejoin_attempts >= self.config['max_autorejoin_attempts']:
            self._logger.warning('autorejoin attempts limit reached, waiting for user interact now')
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

    def on_whoisuser(self, _, raw_msg):
        """ called by super() when WHOIS response arrives """
        self._call_plugins_methods('whoisuser', raw_msg=raw_msg, nick=irc_nickname(raw_msg.arguments[0]), user=irc_nickname(raw_msg.arguments[1]), host=irc_nickname(raw_msg.arguments[2]))

    def on_nick(self, _, raw_msg):
        """ called by super() when somebody changes nickname """
        self._call_plugins_methods('nick', raw_msg=raw_msg, source=raw_msg.source, old_nickname=irc_nickname(raw_msg.source.nick), new_nickname=irc_nickname(raw_msg.target))

    def on_part(self, _, raw_msg):
        """ called by super() when somebody lefts channel """
        self._call_plugins_methods('part', raw_msg=raw_msg, source=raw_msg.source)

    def on_ctcp(self, _, raw_msg):
        """ called by super() when ctcp arrives (/me ...) """
        self._call_plugins_methods('ctcp', raw_msg=raw_msg, source=raw_msg.source, msg=raw_msg.arguments[1] if len(raw_msg.arguments) > 1 else '')

    def on_namreply(self, _, raw_msg):
        """ called by super() when NAMES response arrives """
        nickname_prefixes = '~&@%+'
        nicks = raw_msg.arguments[2].split()
        for i in range(0, len(nicks)):
            for prefix in nickname_prefixes:
                if nicks[i].startswith(prefix): nicks[i] = nicks[i][1:].strip()

        self._call_plugins_methods('namreply', raw_msg=raw_msg, nicknames=nicks)

    # don't touch this

    def _login(self):
        # TODO add more login ways
        # TODO plugin
        # TODO if freenode...

        if 'password' in self.config and self._nickname_id < len(self.config['password']):
            password = self.config['password'][self._nickname_id]
            if password is not None and password != '':
                self._logger.info(f'identifying as {self.get_nickname()}...')
                self.say('NickServ', f'identify {self.get_nickname()} {password}')
        else:
            self._logger.debug(f'no password provided for {self.config["nickname"][self._nickname_id]}')

    def _sigint_handler(self, signal, frame):
        if not self._dying:
            self._logger.info(f'interrupted by user, dying...')
            self.die()

    def _atexit(self):
        if not self._dying:
            self._logger.info(f'interrupted, dying...')
            self.die()

    def _get_best_command_match(self, command, sender_nick):
        choices = [c.replace('_', ' ') for c in self.get_commands() if not (hasattr(self.get_commands()[c], '__admin') and not self.is_user_op(sender_nick))]
        command = command.replace('_', ' ')
        result = process.extract(command, choices, scorer=fuzz.token_sort_ratio)
        result = [(r[0].replace(' ', '_'), r[1]) for r in result]
        return result[0][0] if result[0][1] > 65 else None

    def _call_plugins_methods(self, func_name, **kwargs):
        func_name = f'on_{func_name.strip()}'
        for p in self.get_plugins():
            try:
                p.__getattribute__(func_name)(**kwargs)
            except Exception as e:
                self._logger.error(f'exception caught calling {p.__getattribute__(func_name).__qualname__}: {type(e).__name__}: {e}')
                if self.is_debug_mode_enabled(): raise

    def _load_plugins(self):
        self._logger.debug('loading plugins...')
        disabled_plugins = self.config['disabled_plugins'] if 'disabled_plugins' in self.config else []
        enabled_plugins = self.config['enabled_plugins'] if 'enabled_plugins' in self.config else [x.__name__ for x in plugin.plugin.__subclasses__()]

        for plugin_class in plugin.plugin.__subclasses__():
            if plugin_class.__name__ in disabled_plugins or plugin_class.__name__ not in enabled_plugins:
                self._logger.info(f'- plugin {plugin_class.__name__} skipped')
                continue

            try:
                plugin_instance = plugin_class(self)
            except utils.config_error as e:
                self._logger.warning(f'- invalid {plugin_class.__name__} plugin config: {type(e).__name__}: {e}')
                if self.is_debug_mode_enabled(): raise
                continue
            except Exception as e:
                self._logger.warning(f'- unable to load plugin {plugin_class.__name__}: {type(e).__name__}: {e}')
                if self.is_debug_mode_enabled(): raise
                continue

            self.register_plugin(plugin_instance)

        self._logger.debug('plugins loaded')

    def _say_dispatcher(self, msg, target, force=False):
        if self.config['flood_protection'] and not force:
            self._say_queue.put(self._say_info(target, msg))

            if self._say_thread is None or not self._say_thread.is_alive():
                self._logger.debug('starting _say_thread...')
                self._say_thread = Thread(target=self._process_say)
                self._say_thread.start()
        else:
            self._say_impl(msg, target)

    def _say_impl(self, msg, target):
        try:
            self.connection.privmsg(target, msg)
        except Exception as e:
            self._logger.error(f'cannot send "{msg}": {type(e).__name__}: {e}. discarding msg...')

    def _process_say(self):
        msgs_sent = 0

        while not self._say_queue.empty() and msgs_sent < 5:
            say_info = self._say_queue.get()
            self._logger.debug(f'sending reply to {say_info.target}: {say_info.msg}')
            self._say_impl(say_info.msg, say_info.target)
            msgs_sent += 1
            self._say_queue.task_done()

        time.sleep(0.5)  # to not get kicked because of Excess Flood

        while not self._say_queue.empty():
            say_info = self._say_queue.get()
            self._logger.debug(f'sending reply to {say_info.target}: {say_info.msg}')
            self._say_impl(say_info.msg, say_info.target)
            time.sleep(0.5)  # to not get kicked because of Excess Flood

        self._logger.debug('no more msgs to send, exiting...')

    def _register_plugin_handlers(self, plugin_instance):
        if plugin_instance not in self._plugins:
            self._logger.error(f'plugin {type(plugin_instance).__name__} not registered, aborting...')
            raise RuntimeError(f'plugin {type(plugin_instance).__name__} not registered!')

        for f in inspect.getmembers(plugin_instance, predicate=inspect.ismethod):
            func = f[1]
            func_name = f[0]
            if hasattr(func, '__command'):
                if func_name in self.get_commands():
                    self._logger.warning(f'command {func_name} already registered, skipping...')
                    continue

                self._commands[func_name] = func
                self._logger.debug(f'command {func_name} registered')

            if hasattr(func, '__regex'):
                __regex = getattr(func, '__regex')
                if __regex not in self._msg_regexps:
                    self._msg_regexps[__regex] = []

                self._msg_regexps[__regex].append(func)
                self._msg_regexps[__regex] = list(set(self._msg_regexps[__regex]))
                self._logger.debug(f'regex for {func.__qualname__} registered: \'{getattr(func, "__regex").pattern}\'')

    def _get_fixed_command(self):
        with self._fixed_command_lock:
            return self._fixed_command

    # API funcs

    def register_plugin(self, plugin_instance):
        """
        register plugin_instance as bot's plugin
        handles multiple plugin_instance registered
        throws RuntimeError if plugin_instance does not inherit from plugin base class
        """
        plugin_name = type(plugin_instance).__name__
        if not issubclass(type(plugin_instance), plugin.plugin):
            self._logger.error(f'trying to register no-plugin class {plugin_name} as plugin, aborting...')
            raise RuntimeError(f'class {plugin_name} does not inherit from plugin!')

        if plugin_instance in self.get_plugins():
            self._logger.warning(f'plugin {plugin_name} already registered, skipping...')
            return

        self._plugins.add(plugin_instance)
        self._logger.info(f'+ plugin {plugin_name} loaded')
        self._register_plugin_handlers(plugin_instance)

    def remove_plugin(self, plugin_instance):
        """
        unload and remove plugin_instance bot plugin
        """
        plugin_name = type(plugin_instance).__name__

        if plugin_instance not in self.get_plugins():
            self._logger.warning(f'plugin {plugin_name} not registered, skipping...')
            return

        try:
            plugin_instance.unload_plugin()
        except Exception as e:
            self._logger.error(f'{plugin_name}.unload_plugin() throws: {type(e).__name__}: {e}. continuing anyway...')
            if self.is_debug_mode_enabled(): raise

        self._plugins.remove(plugin_instance)

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
            return [x for x in self.get_commands() if type(self.get_commands()[x].__self__).__name__ == plugin_name]
        else:
            return None

    def get_plugin(self, plugin_name):
        """
        :return: registered plugin instance with name plugin_name or None
        """
        try:
            return next(x for x in self.get_plugins() if x.__class__.__name__ == plugin_name)
        except StopIteration:
            return None

    def get_plugins(self):
        """
        :return: registered plugins
        """
        return self._plugins

    def get_commands(self):
        """
        :return: registered commands: map {command -> func}
        """
        return self._commands

    def get_msg_regexps(self):
        """
        :return: registered msg regexps: map {regex -> [funcs]}
        """
        return self._msg_regexps

    def get_plugins_names(self):
        """
        :return: names of registered plugins
        """
        return [type(p).__name__ for p in self.get_plugins()]

    def get_usernames_on_channel(self):
        """
        :return: names of users in channel
        """
        return [irc_nickname(x) for x in list(self.channel.users())]

    def is_msg_too_long(self, msg):
        """
        IRC protocol defines 512 as max length of message
        handles utf-8 encoding and additional information required
        """
        msg = f"PRIVMSG {self.config['channel']} :{msg}"
        encoded_msg = msg.encode('utf-8')
        return len(encoded_msg + b'\r\n') > 512  # max msg len defined by IRC protocol

    def is_debug_mode_enabled(self):
        return self._debug_mode

    def joined_to_channel(self):
        return self.connection.is_connected() and self.channel

    def register_fixed_command(self, fixed_command):
        """
        register command to be executed after 'fix' command came
        fixed_command SHOULD NOT start with bot command prefix
        set None to clear fixed command
        """
        self._logger.info(f'saving fixed command: {fixed_command}')
        with self._fixed_command_lock:
            self._fixed_command = fixed_command

    def ignore_user(self, nickname):
        if self.is_user_op(nickname): return

        with self._db_mutex:
            self._db_cursor.execute(f"INSERT OR REPLACE INTO '{self._db_ignored_users_tablename}' VALUES (?)", (nickname,))
            self._db_connection.commit()

    def unignore_user(self, nickname):
        with self._db_mutex:
            self._db_cursor.execute(f"DELETE FROM '{self._db_ignored_users_tablename}' WHERE nickname = ? COLLATE NOCASE", (nickname,))
            self._db_connection.commit()

    def get_ignored_users(self):
        with self._db_mutex:
            self._db_cursor.execute(f"SELECT nickname FROM '{self._db_ignored_users_tablename}'")
            result = self._db_cursor.fetchall()

        return [irc_nickname(n[0]) for n in result]

    def is_user_ignored(self, nickname):
        return irc_nickname(nickname) in self.get_ignored_users() and not self.is_user_op(nickname)

    def add_op(self, nickname):
        if self.is_user_ignored(nickname): self.unignore_user(nickname)
        if irc_nickname(nickname) == self.config['superop']: return

        with self._db_mutex:
            self._db_cursor.execute(f"INSERT OR REPLACE INTO '{self._db_ops_tablename}' VALUES (?)", (nickname,))
            self._db_connection.commit()

    def rm_op(self, nickname):
        if irc_nickname(nickname) == self.config['superop']: return

        with self._db_mutex:
            self._db_cursor.execute(f"DELETE FROM '{self._db_ops_tablename}' WHERE nickname = ? COLLATE NOCASE", (nickname,))
            self._db_connection.commit()

    def get_ops(self):
        with self._db_mutex:
            self._db_cursor.execute(f"SELECT nickname FROM '{self._db_ops_tablename}'")
            result = self._db_cursor.fetchall()

        return [irc_nickname(n[0]) for n in result] + [self.config['superop']]

    def is_user_op(self, nickname):
        return irc_nickname(nickname) in self.get_ops()

    @property
    def channel(self):
        return self.channels[self.config['channel']] if self.config['channel'] in self.channels else None

    def die(self, *args, **kwargs):
        if not self._dying:
            self._dying = True
            super().die(*args, **kwargs)

    # connection API funcs

    def join_channel(self):
        self._logger.info(f'joining {self.config["channel"]}...')
        self.connection.join(self.config['channel'])

    def say(self, msg, target=None, force=False):
        """
        send public message to channel or private one to target if specified
        block until message delivered if force param is true
        does nothing if msg is None
        throws MessageTooLong if wrap_too_long_msgs config entry is false
        """
        if not msg: return
        if not target: target = self.config['channel']
        if type(msg) is bytes: msg = msg.decode('utf-8')
        if not isinstance(msg, str): msg = str(msg)

        if self.is_msg_too_long(msg):
            if not self.config['wrap_too_long_msgs']:
                self._logger.debug('privmsg too long, discarding...')
                raise MessageTooLong(msg)

            self._logger.debug('privmsg too long, wrapping...')
            for part in textwrap.wrap(msg, 450):
                self._say_dispatcher(part, target, force)
        else:
            self._say_dispatcher(msg, target, force)

    def say_ok(self, target=None, force=False):
        okies = ['okay', 'okay then', ':)', 'okies!', 'fine', 'done', 'can do!', 'alright', 'sure', 'aight', 'lemme take care of that for you', 'k', 'np']
        self.say(random.choice(okies), target, force)

    def say_err(self, ctx=None, target=None, force=False):
        errs = ["you best check yo'self!", "I can't do that Dave", 'who knows?', "don't ask me", '*shrug*', '...eh?', 'no idea', 'no clue', 'beats me', 'dunno']
        errs_ctx = ['I know nothing about %s', "I can't help you with %s", 'I never heard of %s :(', "%s? what's that then?"]
        self.say(random.choice(errs_ctx) % ctx) if ctx else self.say(random.choice(errs), target, force)

    def leave_channel(self):
        self._logger.info(f'leaving {self.config["channel"]}...')
        self.connection.part(self.config['channel'])

    def get_nickname(self):
        return irc_nickname(self.connection.get_nickname())

    def whois(self, targets):
        return self.connection.whois(targets)

    def whowas(self, nick, max=""):
        return self.connection.whowas(nick, max, self.config['server'])

    def userhost(self, nicks):
        return self.connection.userhost(nicks)

    def notice(self, msg, target=None):
        if not target: target = self.config['channel']
        return self.connection.notice(target, msg)

    def invite(self, nick):
        return self.connection.invite(nick, self.config['channel'])

    def kick(self, nick, comment=''):
        return self.connection.kick(self.config['channel'], nick, comment)

    def list(self):
        return self.connection.list([self.config['channel']], self.config['server'])

    def names(self):
        return self.connection.names([self.config['channel']])

    def set_topic(self, channel, new_topic=None):
        return self.connection.topic(self.config['channel'], new_topic)

    def set_nick(self, new_nick):
        return self.connection.nick(new_nick)

    def mode(self, target, command):
        return self.connection.mode(target, command)

    def disconnect(self, message=''):
        return self.connection.disconnect(message)

    def is_connected(self):
        return self.connection.is_connected()
