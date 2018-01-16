import json
import os
import sys
import shutil
import git
import copy
import requests
import collections

from ruamel import yaml
from irc.client import NickMask
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.parser import ParserError
from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.pybot_dir = os.path.dirname(os.path.realpath(__file__))
        self.pybot_dir = os.path.abspath(os.path.join(self.pybot_dir, os.pardir))
        self.commands_as_other_user_to_send = []

    class as_other_user_command:
        def __init__(self, sender_nick, hacked_nick, connection, raw_msg):
            self.sender_nick = irc_nickname(sender_nick)
            self.hacked_nick = irc_nickname(hacked_nick)
            self.connection = connection
            self.raw_msg = raw_msg

    @command
    @doc('help <entry>: give doc msg for <entry> command / plugin or get supported commands if <entry> is empty')
    def help(self, sender_nick, args, **kwargs):
        if args and args[0]:
            entry = args[0].strip()
            if entry in self.bot.commands:
                self.help_for_command(entry)
            elif entry in self.bot.get_plugins_names():
                self.help_for_plugin(entry)
            else:
                self.bot.say(f'no such command: {entry}')
            self.logger.info(f'help of {args[0]} given for {sender_nick}')
        else:
            self.help_general(sender_nick)
            self.logger.info(f'help given for {sender_nick}')

    def help_general(self, sender_nick):
        commands = self.bot.get_commands_by_plugin()
        commands = collections.OrderedDict(sorted(commands.items()))
        self.bot.say(f'{sender_nick}: check your privmsg!')

        for reply in [cmd for cmd in commands if commands[cmd]]:
            self.bot.say(f'available commands for {reply}: {", ".join(commands[reply])}', sender_nick)

    def help_for_command(self, entry):
        obj = self.bot.commands[entry]

        if hasattr(obj, '__doc_string'):
            for reply in getattr(obj, "__doc_string").split('\n'):
                self.bot.say(color.orange(f'[{entry}] ') + reply.strip())
        else:
            self.bot.say(f'no help for {entry}')

    def help_for_plugin(self, entry):
        plugin = self.bot.get_plugin(entry)

        if hasattr(plugin, '__doc_string'):
            for reply in getattr(plugin, "__doc_string").split('\n'):
                self.bot.say(color.orange(f'[{entry}] ') + reply.strip())
        else:
            self.bot.say(color.orange(f'[{entry}] ') + f'available commands: {", ".join(self.bot.get_plugin_commands(entry))}')

    @command
    @doc('give pybot source code URL')
    def source(self, sender_nick, **kwargs):
        self.logger.info(f'source {self.config["source"]} given to {sender_nick}')
        self.bot.say(f'Patches are welcome! {self.config["source"]}')

    @command
    @admin
    @doc('add_op <nickname>...: add bot operator')
    def add_op(self, sender_nick, args, **kwargs):
        if not args: return
        to_add = [irc_nickname(arg) for arg in args]
        self.bot.config['ops'].extend(to_add)
        reply = f'{to_add[0]} is now op' if len(to_add) == 1 else f'{to_add} are now ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} added new ops: {to_add}')

    @command
    @admin
    @doc('rm_op <nickname>...: remove bot operator')
    def rm_op(self, sender_nick, args, **kwargs):
        to_remove = [irc_nickname(arg) for arg in args]
        to_remove = [arg for arg in to_remove if arg in self.bot.config['ops']]
        if not to_remove: return
        for arg in to_remove:
            self.bot.config['ops'].remove(arg)

        reply = f'{to_remove[0]} is no longer op' if len(to_remove) == 1 else f'{to_remove} are no longer ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} removed ops: {to_remove}')

    @command
    @admin
    @doc('get bot operators')
    def ops(self, sender_nick, **kwargs):
        if len(self.bot.config['ops']) == 0:
            reply = 'no bot operators'
        else:
            reply = f'bot operators: {self.bot.config["ops"]}'

        self.bot.say(reply)
        self.logger.info(f'{sender_nick} asked for ops: {self.bot.config["ops"]}')

    @command
    @admin
    @doc('enable colorful answers')
    def enable_colors(self, sender_nick, **kwargs):
        color.enable_colors()
        self.logger.info(f'{sender_nick} enables colors')
        self.bot.say_ok()

    @command
    @admin
    @doc('disable colorful answers')
    def disable_colors(self, sender_nick, **kwargs):
        color.disable_colors()
        self.logger.info(f'{sender_nick} disables colors')
        self.bot.say_ok()

    @command
    @admin
    @doc('change_log_level <file|stdout> <level>: change logging level')
    def change_log_level(self, sender_nick, args, **kwargs):
        if len(args) < 2: return
        handler_name = args[0].casefold()
        level_name = args[1].casefold()

        if level_name not in utils.logging_level_str_to_int:
            self.bot.say(f'unknown level: {level_name}, supported levels: {", ".join(utils.logging_level_str_to_int.keys())}')
            return

        root_logger = logging.getLogger('')
        level = utils.logging_level_str_to_int[level_name]
        try:
            if handler_name == 'stdout':
                next((x for x in root_logger.handlers if type(x) is logging.StreamHandler)).setLevel(level)
            elif handler_name == 'file':
                next((x for x in root_logger.handlers if type(x) is logging.FileHandler)).setLevel(level)
            else:
                self.bot.say(f'unknown handler: {handler_name}, supported handlers: stdout, file')
                return
        except StopIteration:
            self.bot.say(f'no {handler_name} registered handler')
            return

        self.logger.warning(f'{sender_nick} changes {handler_name} logging level to {level_name}')
        self.bot.say_ok()

    def is_restart_unsafe(self):
        """
        :returns: reason why restart is not safe or None if it is
        """
        try:
            # TODO pip requirements!
            config = yaml.load(open('pybot.yaml'), Loader=yaml.Loader)
            utils.ensure_config_is_ok(config)
            # more asserts should be placed here
        except utils.config_error as e:
            return f'invalid config value: {e}'
        except Exception as e:
            self.logger.error(f'unexpected exception: {e}')
            return 'internal error occurred'

        return None

    @command
    @admin
    @doc('restart [<force>]: restart pybot app, use force to disable consistency checks')
    def restart(self, sender_nick, args, **kwargs):
        reason = self.is_restart_unsafe()
        if reason and not (args and args[0].strip().casefold() == 'force'):
            self.bot.say(f'{reason}, aborting restart, use \'{self.bot.config["command_prefix"]}restart force\' to ignore it')
            return

        self.bot.say("I'll be back soon...", force=True)
        self.restart_impl(sender_nick)

    def restart_impl(self, sender_nick=None):
        args = sys.argv[:]
        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = [f'"{arg}"' for arg in args]

        sender_nick = f' by {sender_nick}' if sender_nick else ''
        self.logger.warning(f"re-spawning '{' '.join(args)}'{sender_nick}")
        os.chdir(os.getcwd())
        os.execv(sys.executable, args)

    def insert_to_config(self, key, value, config):
        """
        inserts :param key -> :param value entry into :param config
        supports dicts nesting (subconfig in config)
        """

        if key not in config:
            config[key] = value
            self.logger.info(f'inserting {key}: {value} to config file')
        elif isinstance(value, dict):  # do not override non-dict values
            for v_key, v_value in value.items():
                self.insert_to_config(v_key, v_value, config[key])

    def remove_obsolete_key_from_config_impl(self, key, config, config_template):
        """
        removes :param key from :param config if it's not present in :param config_template
        supports dicts nesting (subconfig in config)
        """

        if key in config_template:
            if isinstance(config[key], dict):
                config[key] = self.remove_obsolete_key_from_config(config[key], config_template[key])
        else:
            self.logger.info(f'removing {key} from config file')
            del config[key]

    def remove_obsolete_key_from_config(self, config, config_template):
        """
        :return :param config without keys not present in :param config_template
        """

        # TODO fix me!
        return config

        new_config = copy.deepcopy(config)
        for key in config.keys():
            self.remove_obsolete_key_from_config_impl(key, new_config, config_template)

        return new_config

    def write_config_file(self, config, outfilename):
        """
        tries to write formatted :param config to :param outfilename
        """

        config = copy.deepcopy(config)
        global_config = CommentedMap()
        plugins_config = CommentedMap()

        for key, value in config.items():
            if type(value) is not dict and type(value) is not CommentedMap:
                global_config[key] = value
            else:
                plugins_config[key] = value

        with open(outfilename, 'w') as outfile:
            yaml.dump(global_config, outfile, Dumper=yaml.RoundTripDumper)
            outfile.write('\n')
            yaml.dump(plugins_config, outfile, Dumper=yaml.RoundTripDumper)

        with open(outfilename, 'r+') as outfile:
            lines = outfile.readlines()
            outfile.truncate(0)
            outfile.seek(0)

            for i, line in enumerate(lines):
                outfile.write(line)
                if line.strip() and line.startswith(' ') and i + 1 < len(lines) and lines[i + 1] and lines[i + 1][0].isalpha():
                    outfile.write('\n')

            outfile.write('\n')

    def update_config_file(self):
        """
        updates and writes to disk pybot.yaml config file with pybot.template.yaml defaults
        throws exception if config is incorrect
        this function is safe, it writes config only if it is correct
        :return: True if config was updated, False otherwise
        """

        config = yaml.load(open('pybot.yaml'), Loader=yaml.RoundTripLoader)
        config_template = yaml.load(open("pybot.template.yaml"), Loader=yaml.Loader)
        if not config: config = {}
        for key, value in config_template.items():
            self.insert_to_config(key, value, config)

        config = self.remove_obsolete_key_from_config(config, config_template)

        if config == self.bot.config: return False

        # seems to be more safe to first save config, then load it and check consistency
        self.write_config_file(config, '.pybot.yaml')

        config = yaml.load(open('.pybot.yaml'), Loader=yaml.Loader)
        utils.ensure_config_is_ok(config)

        shutil.copyfile('.pybot.yaml', 'pybot.yaml')
        self.logger.warning('config file updated')
        return True

    @command
    @admin
    @doc('updated config with config template defaults and ** restarts **, should be used with caution!')
    def update_config(self, sender_nick, **kwargs):
        shutil.copyfile('pybot.yaml', '..pybot.yaml')

        try:
            self.update_config_file()
            reason = self.is_restart_unsafe()
            if reason:
                self.bot.say(f'restart is unsafe: {reason}, aborting process...')
                shutil.copyfile('..pybot.yaml', 'pybot.yaml')
                return

            self.bot.say('config updated, restarting...', force=True)
            self.restart_impl(sender_nick)
        except utils.config_error as e:
            self.bot.say(f'invalid config value: {e}, aborting...')
            shutil.copyfile('..pybot.yaml', 'pybot.yaml')
        except Exception as e:
            self.logger.error(f'exception caught while updating config file: {e}')
            self.bot.say('cannot update config file, aborting...')
            shutil.copyfile('..pybot.yaml', 'pybot.yaml')
            if self.bot.is_debug_mode_enabled(): raise

    @command
    @admin
    @doc('self_update [<force>]: pull changes from git remote ref and update config file, use [<force>] to discard local changes')
    def self_update(self, sender_nick, args, **kwargs):
        # TODO pip requirements update
        # TODO transactional update?
        self.logger.info(f'{sender_nick} asked for self-update')
        repo = git.Repo(self.pybot_dir)
        origin = repo.remote()
        force_str = ''

        if repo.head.commit.diff(None):  # will not count files added to working tree
            if args and args[0].strip().casefold() == 'force':
                self.logger.warning(f'discarding local changes: {[x.a_path for x in repo.head.commit.diff(None)]}')
                repo.head.reset(commit=repo.head.commit, index=True, working_tree=True)
                force_str = ', local changes discarded'
            else:
                self.bot.say(f'local changes prevents me from update, use \'{self.bot.config["command_prefix"]}self_update force\' to discard them')
                self.logger.info(f'cannot self-update, local changes: {[x.a_path for x in repo.head.commit.diff(None)]}')
                return

        if repo.git.cherry('-v'):
            self.bot.say('local changes prevents me from update')
            self.logger.info(f'cannot self-update, not pushed changes')
            return

        origin.fetch()
        origin.pull()
        if repo.head.orig_head().commit == repo.head.commit:
            self.logger.info(f'already up-to-date at {repo.head.commit}')
            self.bot.say(f'already up-to-date at "{str(repo.head.commit)[:6]}: {repo.head.commit.message.strip()}"')
            return

        self.logger.warning(f'updated {repo.head.orig_head().commit} -> {repo.head.commit}')
        diff_str = f', diffs in {", ".join([x.a_path for x in repo.head.commit.diff(repo.head.orig_head().commit)])}'

        try:
            if self.update_config_file(): config_updated_str = ', config file updated'
            else: config_updated_str = ''

        except Exception as e:
            self.logger.error(f'exception caught while updating config file: {e}. getting back to {repo.head.orig_head().commit}')
            self.bot.say('cannot update config file, aborting...')
            repo.head.reset(commit=repo.head.orig_head().commit, index=True, working_tree=True)
            if self.bot.is_debug_mode_enabled(): raise
            return

        self.bot.say(f'updated, now at "{str(repo.head.commit)[:6]}: {repo.head.commit.message.strip()}"{config_updated_str}{diff_str}{force_str}')
        repo.head.orig_head().set_commit(repo.head)

    def on_whoisuser(self, nick, user, host, **kwargs):
        cmds = self.commands_as_other_user_to_send
        try:
            args = next(x for x in cmds if x.hacked_nick == nick)
        except StopIteration: return

        hacked_source = NickMask.from_params(args.hacked_nick, user, host)
        hacked_raw_msg = args.raw_msg
        hacked_raw_msg.source = hacked_source
        hacked_raw_msg.arguments = (hacked_raw_msg.arguments[0],)

        self.logger.warning(f'{args.sender_nick} runs command ({hacked_raw_msg.arguments[0]}) as {args.hacked_nick}')
        self.commands_as_other_user_to_send.remove(args)

        self.bot.on_pubmsg(args.connection, hacked_raw_msg)

    def clean_commands_as_other_user_to_send(self):
        users = self.bot.get_usernames_on_channel()

        for x in self.commands_as_other_user_to_send:
            if x.hacked_nick not in users:
                self.logger.info(f'removing {x.sender_nick} command ({x.raw_msg.arguments[0]}) as {x.hacked_nick}')
                self.commands_as_other_user_to_send.remove(x)

    @command
    @admin
    @doc('as_other_user <username> <message>: emulate sending <message> as <username>, requires <username> to be online')
    def as_other_user(self, sender_nick, msg, raw_msg, **kwargs):
        if not msg: return
        hacked_nick = irc_nickname(msg.split()[0])
        new_msg = msg[len(hacked_nick):].strip()
        raw_msg.arguments = (new_msg, raw_msg.arguments[1:])
        self.logger.info(f'{sender_nick} queued command ({new_msg}) as {hacked_nick}')
        self.commands_as_other_user_to_send.append(self.as_other_user_command(sender_nick, hacked_nick, self.bot.connection, raw_msg))

        # now we don't know ho to set raw_msg fields (user and host)
        # that's why we are queuing this call, then calling /whois hacked_user
        # when /whois response received, we've got needed user and host so we can do appropriate call
        self.clean_commands_as_other_user_to_send()
        self.bot.whois(hacked_nick)

    @command
    @admin
    @doc('change_config <entry> <value>: change, save, apply bot config file and ** restart **. use ":" to separate config nesting (eg. "a:b:c" means config["a"]["b"]["c"])')
    def change_config(self, msg, sender_nick, **kwargs):
        if not msg: return
        keys = msg.split()[0].split(':')
        keys = [k.strip() for k in keys]
        if not keys: return
        value = msg[len(msg.split()[0]):].strip()
        try:
            value = yaml.load(value, Loader=yaml.RoundTripLoader)
        except ParserError:
            self.bot.say(f'cannot parse value: {value}')
            return

        config = yaml.load(open('pybot.yaml'), Loader=yaml.RoundTripLoader)
        config_entry = config

        for key_it, key in enumerate(keys):
            if key not in config_entry:
                self.bot.say(f'no such key: {msg.split()[0]}')
                return

            if key_it == len(keys) - 1:
                config_entry[key] = value
            else:
                config_entry = config_entry[key]

        # seems to be more safe to first save config, then load it and check consistency
        self.write_config_file(config, '.pybot.yaml')

        config = yaml.load(open('.pybot.yaml'), Loader=yaml.Loader)

        try:
            utils.ensure_config_is_ok(config)
        except utils.config_error as e:
            self.bot.say(f'invalid value: {e}, aborting...')
            return

        reason = self.is_restart_unsafe()
        if reason:
            self.bot.say(f'restart is unsafe: {reason}, aborting...')
            return

        shutil.copyfile('.pybot.yaml', 'pybot.yaml')
        self.logger.warning(f'{sender_nick} changed config entry {keys} = {value}')
        self.bot.say('config entry applied, restarting...', force=True)
        self.restart_impl(sender_nick)

    def upload_file_impl(self, sender_nick, filename):
        if not os.path.isfile(filename):
            self.bot.say(f'no {filename} file found')
            return

        with open(filename) as file:
            raw_response = requests.post(r'http://file.io/?expires=1w', files={r'file': file}).content.decode('utf-8')
            response = json.loads(raw_response)
            if not response['success'] or 'link' not in response:
                self.bot.say('file.io error')
                self.logger.info(f'file.io returned error for {sender_nick}: {response}')
            else:
                self.bot.say(f'{sender_nick}: check your privmsg!')
                self.bot.say(response['link'], sender_nick)
                self.logger.info(f'{filename} uploaded to file.io for {sender_nick}: {response["link"]}')

    @command
    @admin
    @doc('uploads error logs to file.io')
    def upload_errors(self, sender_nick, **kwargs):
        self.upload_file_impl(sender_nick, r'pybot.error')

    @command
    @admin
    @doc('uploads log file to file.io')
    def upload_logs(self, sender_nick, **kwargs):
        self.upload_file_impl(sender_nick, r'pybot.log')

    @command
    @doc("fix your previous command")
    def fix(self, **kwargs):
        """
        just a placeholder for fix functionality. Its implementation has to be placed in pybot.on_pubmsg
        """
