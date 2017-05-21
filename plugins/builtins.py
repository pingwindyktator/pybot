import os
import subprocess
import sys
import shutil
import git

from ruamel import yaml
from threading import Lock
from irc.client import NickMask
from ruamel.yaml.comments import CommentedMap
from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.pybot_dir = os.path.dirname(os.path.realpath(__file__))
        self.pybot_dir = os.path.abspath(os.path.join(self.pybot_dir, os.pardir))
        self.commands_as_other_user_to_send = []
        self.mutex = Lock()

    class as_other_user_command:
        def __init__(self, sender_nick, hacked_nick, connection, raw_msg):
            self.sender_nick = irc_nickname(sender_nick)
            self.hacked_nick = irc_nickname(hacked_nick)
            self.connection = connection
            self.raw_msg = raw_msg

    @command
    def help(self, sender_nick, args, **kwargs):
        if args and args[0]:
            func_name = args[0]
            if func_name not in self.bot.commands:
                return

            func = self.bot.commands[func_name]
            if hasattr(func, '__doc_string'):
                self.bot.say(getattr(func, "__doc_string"))
            else:
                self.bot.say(f'no help for {func_name}')

            self.logger.info(f'help of {func_name} given for {sender_nick}')

        else:
            commands = self.bot.get_commands_by_plugin()
            for p in commands:
                if commands[p]:
                    self.bot.say(f'available commands for {p}: {", ".join(commands[p])}')

            self.logger.info(f'help given for {sender_nick}')

    @command
    def source(self, sender_nick, **kwargs):
        self.logger.info(f'source {self.config["source"]} given to {sender_nick}')
        self.bot.say(f'Patches are welcome! {self.config["source"]}')

    @command
    @admin
    def add_op(self, sender_nick, args, **kwargs):
        if not args: return
        to_add = [irc_nickname(arg) for arg in args]
        self.bot.config['ops'].extend(to_add)
        reply = f'{to_add[0]} is now op' if len(to_add) == 1 else f'{to_add} are now ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} added new ops: {to_add}')

    @command
    @admin
    def rm_op(self, sender_nick, args, **kwargs):
        if not args: return
        to_remove = [irc_nickname(arg) for arg in args]
        to_remove = [arg for arg in to_remove if arg in self.bot.config['ops']]
        for arg in to_remove:
            self.bot.config['ops'].remove(arg)

        reply = f'{to_remove[0]} is no longer op' if len(to_remove) == 1 else f'{to_remove} are no longer ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} removed ops: {to_remove}')

    @command
    @admin
    def ops(self, sender_nick, **kwargs):
        if len(self.bot.config['ops']) == 0:
            reply = 'no bot operators'
        else:
            reply = f'bot operators: {self.bot.config["ops"]}'

        self.bot.say(reply)
        self.logger.info(f'{sender_nick} asked for ops: {self.bot.config["ops"]}')

    @command
    @admin
    def ban_user(self, sender_nick, args, **kwargs):
        if not args: return
        to_ban = [irc_nickname(arg) for arg in args]
        if 'banned_users' not in self.bot.config:
            self.bot.config['banned_users'] = to_ban
        else:
            self.bot.config['banned_users'].extend(to_ban)

        reply = f'{to_ban[0]} is now banned' if len(to_ban) == 1 else f'{to_ban} are now banned'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} banned {to_ban}')

    @command
    @admin
    def unban_user(self, sender_nick, args, **kwargs):
        if not args: return
        if 'banned_users' not in self.bot.config: return
        to_ban = [irc_nickname(arg) for arg in args]
        to_ban = [arg for arg in to_ban if arg in self.bot.config['banned_users']]
        for arg in to_ban:
            self.bot.config['banned_users'].remove(arg)

        reply = f'{to_ban[0]} is no longer banned' if len(to_ban) == 1 else f'{to_ban} are no longer banned'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} unbaned: {to_ban}')

    @command
    @admin
    def banned_users(self, sender_nick, **kwargs):
        banned = self.bot.config['banned_users'] if 'banned_users' in self.bot.config else []

        if len(banned) == 0:
            reply = 'no banned users'
        else:
            reply = f'banned users: {banned}'

        self.bot.say(reply)
        self.logger.info(f'{sender_nick} asked for banned users: {banned}')

    @command
    @admin
    def restart(self, sender_nick, **kwargs):
        args = sys.argv[:]

        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = [f'"{arg}"' for arg in args]

        self.logger.warning(f"re-spawning '{' '.join(args)}' by {sender_nick}")
        os.chdir(os.getcwd())
        os.execv(sys.executable, args)

    def update_config_impl(self, key, value, config):
        if key not in config:
            config[key] = value
            self.logger.info(f'inserting {key}:{value} to config file')
        elif type(value) is dict:  # do not override non-dict values
            for v_key, v_value in value.items():
                self.update_config_impl(v_key, v_value, config[key])

    def format_and_save_config(self, config, outfilename):
        config = config.copy()
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

    def update_config(self):
        config = yaml.load(open('./pybot.yaml'), Loader=yaml.RoundTripLoader)
        if not config: config = {}
        for key, value in yaml.load(open("./pybot.template.yaml"), Loader=yaml.Loader).items():
            self.update_config_impl(key, value, config)

        if config == self.bot.config: return False
        self.format_and_save_config(config, './.pybot.yaml')

        _config = yaml.load(open('./.pybot.yaml'))
        utils.ensure_config_is_ok(_config)

        shutil.copyfile('./.pybot.yaml', './pybot.yaml')
        self.bot.config = config
        self.logger.warning('config file updated')
        return True

    @command
    @admin
    def self_update(self, sender_nick, args, **kwargs):
        # TODO pip requirements update
        # TODO transactional update?
        self.logger.info(f'{sender_nick} asked for self-update')
        repo = git.Repo(self.pybot_dir)
        origin = repo.remote()
        force_str = ''

        if repo.head.commit.diff(None):  # will not count files added to working tree
            if len(args) > 0 and args[0].strip() == 'force':
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
            self.logger.info(f'already up to date at {repo.head.commit}')
            self.bot.say(f'already up to date at "{str(repo.head.commit)[:6]}: {repo.head.commit.message.strip()}"')
            return

        self.logger.warning(f'updated {repo.head.orig_head().commit} -> {repo.head.commit}')
        diff_str = f', diffs at {", ".join([x.a_path for x in repo.head.commit.diff(repo.head.orig_head().commit)])}'

        try:
            if self.update_config(): config_updated_str = ', config file updated'
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
        cmds = self.commands_as_other_user_to_send.copy()
        try:
            args = (x for x in cmds if
                    x.hacked_nick == nick).__next__()
        except StopIteration: return

        hacked_source = NickMask.from_params(args.hacked_nick, user, host)
        hacked_raw_msg = args.raw_msg
        hacked_raw_msg.source = hacked_source
        hacked_raw_msg.arguments = (hacked_raw_msg.arguments[0],)

        self.logger.warning(
            f'{args.sender_nick} runs command ({hacked_raw_msg.arguments[0]}) as {args.hacked_nick}')
        with self.mutex:
            self.commands_as_other_user_to_send.remove(args)

        self.bot.on_pubmsg(args.connection, hacked_raw_msg)

    def clean_commands_as_other_user_to_send(self):
        users = list(self.bot.channel.users())

        with self.mutex:
            for x in self.commands_as_other_user_to_send:
                if x.hacked_nick not in users:
                    self.logger.info(f'removing {x.sender_nick} command ({x.raw_msg.arguments[0]}) as {x.hacked_nick}')
                    self.commands_as_other_user_to_send.remove(x)

    @command
    @admin
    def as_other_user(self, sender_nick, msg, raw_msg, **kwargs):
        if not msg: return
        hacked_nick = irc_nickname(msg.split()[0])
        new_msg = msg[len(hacked_nick):].strip()
        raw_msg.arguments = (new_msg, raw_msg.arguments[1:])
        self.logger.info(f'{sender_nick} queued command ({new_msg}) as {hacked_nick}')
        with self.mutex:
            self.commands_as_other_user_to_send.append(self.as_other_user_command(sender_nick, hacked_nick, self.bot.connection, raw_msg))

        # now we don't know ho to set raw_msg fields (user and host)
        # that's why we are queuing this call, then calling /whois hacked_user
        # when /whois response received, we've got needed user and host and we can do appropriate call
        self.clean_commands_as_other_user_to_send()
        self.bot.whois(hacked_nick)
