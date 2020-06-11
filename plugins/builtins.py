import os
import sys
import shutil
import git
import copy
import requests
import collections

from datetime import datetime
from ruamel import yaml
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.parser import ParserError
from plugin import *


class builtins(plugin):
    @command
    @doc("""help <entry>: get doc msg for <entry> command / plugin
            get general help""")
    def help(self, sender_nick, args, **kwargs):
        if args and args[0]:
            entry = args[0].strip()
            if entry in self.bot.get_commands():
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
        if 'help' in self.config and self.config['help']:
            self.bot.say(f'Here you go: {self.config["help"]}')
        else:
            commands = self.bot.get_commands_by_plugin()
            commands = collections.OrderedDict(sorted(commands.items()))
            self.bot.say(f'{sender_nick}: check your privmsg!')

            for reply in [cmd for cmd in commands if commands[cmd]]:
                self.bot.say(f'available commands for {color.blue(reply)}: {", ".join(sorted(commands[reply]))}', sender_nick)

    def help_for_command(self, entry):
        obj = self.bot.get_commands()[entry]

        if hasattr(obj, '__doc_string'):
            for reply in getattr(obj, "__doc_string").split('\n'):
                self.bot.say(color.orange(f'[{entry}] ') + reply.strip())
        else:
            self.bot.say(f'no help for {entry}')

    def help_for_plugin(self, entry):
        plugin_instance = self.bot.get_plugin(entry)

        if hasattr(plugin_instance, '__doc_string'):
            for reply in getattr(plugin_instance, "__doc_string").split('\n'):
                self.bot.say(color.orange(f'[{entry}] ') + reply.strip())
        else:
            self.bot.say(color.orange(f'[{entry}] ') + f'available commands: {", ".join(self.bot.get_plugin_commands(entry))}')

    @command
    @doc('give pybot source code URL')
    def source(self, sender_nick, **kwargs):
        self.logger.info(f'source given to {sender_nick}')
        if 'source' in self.config and self.config['source']:
            self.bot.say(f'Patches are welcome! {self.config["source"]}')
        else:
            self.bot.say('no source URL provided :(')

    @command(admin=True)
    @doc('enable colorful answers')
    def enable_colors(self, sender_nick, **kwargs):
        color.enable_colors()
        self.logger.info(f'{sender_nick} enables colors')
        self.bot.say_ok()

    @command(admin=True)
    @doc('disable colorful answers')
    def disable_colors(self, sender_nick, **kwargs):
        color.disable_colors()
        self.logger.info(f'{sender_nick} disables colors')
        self.bot.say_ok()

    @command(superadmin=True)
    @doc('enable debug mode')
    def enable_debug_mode(self, sender_nick, **kwargs):
        self.bot.set_debug_mode(True)
        self.logger.warning(f'{sender_nick} enables debug mode')
        self.bot.say_ok()

    @command(superadmin=True)
    @doc('disable debug mode')
    def disable_debug_mode(self, sender_nick, **kwargs):
        self.bot.set_debug_mode(False)
        self.logger.warning(f'{sender_nick} disables debug mode')
        self.bot.say_ok()

    @command(admin=True)
    @doc('change_log_level <file|stdout> <level>: change logging level')
    def change_log_level(self, sender_nick, args, **kwargs):
        if len(args) < 2: return
        handler_name = args[0].casefold()
        level_name = args[1].casefold()

        if level_name not in utils.logging_level_str_to_int:
            self.bot.say(f'unknown level: {level_name}, supported levels: {", ".join(utils.logging_level_str_to_int.keys())}')
            return

        root_logger = logging.getLogger()
        level = utils.logging_level_str_to_int[level_name]
        try:
            if handler_name == 'stdout':
                next((x for x in root_logger.handlers if isinstance(x, logging.StreamHandler))).setLevel(level)
            elif handler_name == 'file':
                next((x for x in root_logger.handlers if isinstance(x, logging.FileHandler))).setLevel(level)
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
            config = yaml.load(open(utils.CONFIG_FILENAME), Loader=yaml.Loader)
        except Exception as e:
            self.logger.info(f'exception: {type(e).__name__}: {e}')
            return 'cannot load config file'

        config_violations = utils.get_config_violations(config)
        if config_violations:
            self.logger.info(f'invalid config file: {config_violations}')
            return 'invalid config file'

        return None

    @command(admin=True)
    @doc('restart [<force>]: restart pybot app, use force to disable consistency checks')
    def restart(self, sender_nick, args, **kwargs):
        reason = self.is_restart_unsafe()
        if reason and not (args and args[0].strip().casefold() == 'force'):
            self.bot.say(f'{reason}, aborting restart, use \'{self.bot.get_command_prefix()}restart force\' to ignore it')
            return

        self.bot.say("I'll be back soon...", force=True)
        self.restart_impl(sender_nick)

    def restart_impl(self, sender_nick):
        args = sys.argv[:]
        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = [f'"{arg}"' for arg in args]

        self.bot.die()
        self.logger.warning(f"re-spawning '{' '.join(args)}' by {sender_nick}")
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
            if not isinstance(value, dict):
                global_config[key] = value
            else:
                plugins_config[key] = value

        with open(outfilename, 'w') as outfile:
            yaml.dump(global_config, outfile, Dumper=yaml.RoundTripDumper)
            outfile.write('\n')
            yaml.dump(plugins_config, outfile, Dumper=yaml.RoundTripDumper)

        with open(outfilename, 'r+') as outfile:
            lines = outfile.readlines()
            # remove doubled newline
            lines = [line for i, line in enumerate(lines) if not (not line.strip() and i + 1 < len(lines) and not lines[i + 1].strip())]
            if lines[-1] != '\n': lines.append('\n')
            outfile.truncate(0)
            outfile.seek(0)

            for i, line in enumerate(lines):
                outfile.write(line)

                if line.strip() and line.startswith(' ') and i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith(' '):
                    # if last entry in plugin's config
                    outfile.write('\n')

    def update_config_file(self):
        """
        updates and writes to disk pybot.yaml config file with pybot.template.yaml defaults
        throws exception if config is incorrect
        this function is safe, it writes config only if it is correct
        :return: True if config was updated, False otherwise
        """

        config = yaml.load(open(utils.CONFIG_FILENAME), Loader=yaml.RoundTripLoader)
        config_template = yaml.load(open(utils.CONFIG_TEMPLATE_FILENAME), Loader=yaml.Loader)
        if not config: config = {}
        for key, value in config_template.items():
            self.insert_to_config(key, value, config)

        config = self.remove_obsolete_key_from_config(config, config_template)

        if config == self.bot.config: return False

        # seems to be more safe to first save config, then load it and check consistency
        self.write_config_file(config, '.pybot.yaml')  # TODO temp file

        config = yaml.load(open('.pybot.yaml'), Loader=yaml.Loader)
        if utils.get_config_violations(config): raise RuntimeError('invalid config file')

        shutil.copyfile('.pybot.yaml', utils.CONFIG_FILENAME)
        self.logger.warning('config file updated')
        return True

    @command(superadmin=True)
    @doc('update config with config template defaults and ** restarts **, should be used with caution!')
    def update_config(self, sender_nick, **kwargs):
        shutil.copyfile(utils.CONFIG_FILENAME, '..pybot.yaml')

        try:
            self.update_config_file()
            reason = self.is_restart_unsafe()
            if reason:
                self.bot.say(f'restart is unsafe: {reason}, aborting process...')
                shutil.copyfile('..pybot.yaml', utils.CONFIG_FILENAME)
                return

            self.bot.say('config updated, restarting...', force=True)
            self.restart_impl(sender_nick)
        except Exception as e:
            self.logger.error(f'exception caught while updating config file: {type(e).__name__}: {e}')
            self.bot.say('cannot update config file, aborting...')
            shutil.copyfile('..pybot.yaml', utils.CONFIG_FILENAME)
            utils.report_error()

    def prepare_commit_msg(self, commit):
        commit_msg = commit.message.strip().replace('\n', '; ')
        return f'{str(commit)[:6]}: {commit_msg}'

    @command(superadmin=True)
    @doc('self_update [<force>]: pull changes from git remote ref and update config file, use [<force>] to discard local changes')
    def self_update(self, sender_nick, args, **kwargs):
        self.logger.info(f'{sender_nick} asked for self-update')

        try:
            repo = git.Repo(utils.get_pybot_dir())
        except git.InvalidGitRepositoryError:
            self.bot.say('not in a git repository, cannot update')
            return

        force_str = ''
        repo.head.orig_head().set_commit(repo.head)

        if repo.head.commit.diff(None):  # will not count files added to working tree
            if args and args[0].strip().casefold() == 'force':
                self.logger.warning(f'discarding local changes: {[x.a_path for x in repo.head.commit.diff(None)]}')
                repo.head.reset(commit=repo.head.commit, index=True, working_tree=True)
                force_str = ', local changes discarded'
            else:
                self.bot.say(f'local changes prevents me from update, use \'{self.bot.get_command_prefix()}self_update force\' to discard them')
                self.logger.info(f'cannot self-update, local changes: {[x.a_path for x in repo.head.commit.diff(None)]}')
                return

        if repo.git.cherry('-v'):
            self.bot.say('local changes prevents me from update')
            self.logger.info(f'cannot self-update, not pushed changes')
            return

        repo.remote().fetch()
        repo.remote().pull()
        if repo.head.orig_head().commit == repo.head.commit:
            self.logger.info(f'already up-to-date at {repo.head.commit}')
            self.bot.say(f'already up-to-date at "{self.prepare_commit_msg(repo.head.commit)}"')
            return

        self.logger.warning(f'updated {repo.head.orig_head().commit} -> {repo.head.commit}')
        diff = [x.a_path for x in repo.head.commit.diff(repo.head.orig_head().commit)]
        plugins_diff = [x[len('plugins/'):-len('.py')] for x in diff if x.startswith('plugins/') and x.endswith('.py')]
        if len(plugins_diff) == len(diff): diff_str = f', you should reload {", ".join(plugins_diff)} {"plugins" if len(plugins_diff) > 1 else "plugin"} now'
        else: diff_str = ', probably you should restart bot now'

        try:
            if self.update_config_file(): config_updated_str = ', config file updated'
            else: config_updated_str = ''

        except Exception as e:
            self.logger.error(f'exception caught while updating config file: {type(e).__name__}: {e}. getting back to {repo.head.orig_head().commit}')
            self.bot.say('cannot update config file, aborting...')
            repo.head.reset(commit=repo.head.orig_head().commit, index=True, working_tree=True)
            utils.report_error()
            return

        self.bot.say(f'updated, now at "{self.prepare_commit_msg(repo.head.commit)}"{config_updated_str}{force_str}{diff_str}')

    @command(superadmin=True)
    @doc('change_config <entry> <value>: change, save, apply bot config file and ** restart **. use ":" to separate config nesting (eg. "a:b:c" means config["a"]["b"]["c"])')
    def change_config(self, msg, sender_nick, **kwargs):
        if not msg: return
        keys = msg.split()[0].split(':')
        keys = [k.strip() for k in keys]
        if not keys: return
        value = msg[len(msg.split()[0]):].strip()
        try:
            value = yaml.load(value, Loader=yaml.RoundTripLoader)
        except ParserError as e:
            self.logger.warning(f'cannot parse value "{value}": {type(e).__name__}: {e}')
            self.bot.say(f'cannot parse value: {value}')
            return

        config = yaml.load(open(utils.CONFIG_FILENAME), Loader=yaml.RoundTripLoader)
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

        config_violations = utils.get_config_violations(config)
        if config_violations:
            self.logger.warning(f'invalid config: {config_violations}, aborting...')
            self.bot.say(f'invalid value, aborting...')
            return

        reason = self.is_restart_unsafe()
        if reason:
            self.bot.say(f'restart is unsafe: {reason}, aborting...')
            return

        shutil.copyfile('.pybot.yaml', utils.CONFIG_FILENAME)
        self.logger.warning(f'{sender_nick} changed config entry {keys} = {value}')
        self.bot.say('config entry applied, restarting...', force=True)
        self.restart_impl(sender_nick)

    @utils.repeat_until(no_exception=True)
    def upload_file_impl(self, filename):
        with open(filename) as file:
            response = requests.post(r'http://file.io/?expires=1w', files={r'file': file}).json()
            if not response['success'] or 'link' not in response:
                raise RuntimeError('file.io error')
            else:
                return response['link']

    def upload_file(self, filename):
        if not os.path.isfile(filename):
            raise RuntimeError(f'{filename}: no such file')

        try:
            return self.upload_file_impl(filename)
        except Exception as e:
            self.logger.debug(f'unable to upload {filename}: {type(e).__name__}: {e}, retrying with last 1000 lines...')

            with open('.upload_file', 'w') as outfile:
                with open(filename) as infile:
                    outfile.writelines(infile.readlines()[-1000:])

            return self.upload_file_impl('.upload_file')

    @command(admin=True)
    @doc('uploads error logs to file.io')
    def upload_errors(self, sender_nick, **kwargs):
        try:
            link = self.upload_file(r'pybot.error')
            self.bot.say(f'{sender_nick}: check your privmsg!')
            self.bot.say(link, sender_nick)
            self.logger.info(f'pybot.error uploaded to file.io for {sender_nick}: {link}')
        except Exception as e:
            self.bot.say(f'unable to upload file')
            self.logger.error(f'unable to upload pybot.error: {type(e).__name__}: {e}')

    @command(admin=True)
    @doc('uploads log file to file.io')
    def upload_logs(self, sender_nick, **kwargs):
        try:
            link = self.upload_file(r'pybot.log')
            self.bot.say(f'{sender_nick}: check your privmsg!')
            self.bot.say(link, sender_nick)
            self.logger.info(f'pybot.log uploaded to file.io for {sender_nick}: {link}')
        except Exception as e:
            self.bot.say(f'unable to upload file')
            self.logger.error(f'unable to upload pybot.log: {type(e).__name__}: {e}')

    @command
    @command_alias('date')
    @doc("get bot's local time")
    def time(self, **kwargs):
        self.bot.say(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + utils.get_str_utc_offset())

    @command
    @doc('fix your previous command')
    def fix(self, **kwargs):
        """
        just a placeholder for fix functionality. Its implementation has to be placed in pybot.on_pubmsg
        """
