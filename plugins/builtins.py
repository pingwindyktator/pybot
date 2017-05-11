import os
import subprocess
import sys

from ruamel import yaml
from threading import Lock
from collections import namedtuple
from irc.client import NickMask
from ruamel.yaml.comments import CommentedMap

from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.pybot_dir = os.path.dirname(os.path.realpath(__file__))
        self.pybot_dir = os.path.abspath(os.path.join(self.pybot_dir, os.pardir))
        self.as_other_user_command = namedtuple('as_other_user_command',
                                                'sender_nick hacked_nick connection raw_msg')
        self.commands_as_other_user_to_send = []
        self.mutex = Lock()

    @command
    def help(self, sender_nick, args, **kwargs):
        if args and args[0]:
            func_name = args[0]
            if func_name not in self.bot.commands:
                return

            func = self.bot.commands[func_name]
            if hasattr(func, '__doc_string'):
                self.bot.say(f'{func_name}: {getattr(func, "__doc_string")}')
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
        self.bot.config['ops'].extend(args)
        reply = f'{args[0]} is now op' if len(args) == 1 else f'{args} are now ops'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} added new ops: {args}')

    @command
    @admin
    def rm_op(self, sender_nick, args, **kwargs):
        to_remove = [arg for arg in args if arg in self.bot.config['ops']]
        if not to_remove: return
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

        if 'banned_users' not in self.bot.config:
            self.bot.config['banned_users'] = args
        else:
            self.bot.config['banned_users'].extend([arg.lower() for arg in args])

        reply = f'{args[0]} is now banned' if len(args) == 1 else f'{args} are now banned'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} banned {args}')

    @command
    @admin
    def unban_user(self, sender_nick, args, **kwargs):
        if 'banned_users' not in self.bot.config: return
        to_ban = [arg.lower() for arg in args if arg.lower() in self.bot.config['banned_users']]
        if not to_ban: return
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

    def update_possible(self):
        cmd1 = f'git -C {self.pybot_dir} diff --exit-code'  # unstaged changes
        process1 = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE)
        process1.wait(2)

        cmd2 = f'git -C {self.pybot_dir} cherry -v | wc -l'  # not committed changes
        process2 = subprocess.Popen(cmd2, shell=True, stdout=subprocess.PIPE)
        out, err = process2.communicate()

        return process1.returncode == 0 and out == b'0\n'

    def get_current_head_pos(self):
        cmd = f"git -C {self.pybot_dir} log --oneline -n 1 | sed 's/ /: /'"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()
        return ''.join([chr(x) for x in list(out)[:-1]])

    def update_config_impl(self, key, value, config):
        """
        :param entry: what to insert to :param config
        """

        if key not in config:
            config[key] = value
            self.logger.info(f'inserting {key}:{value} to config file')
        elif type(value) is dict:  # do not override non-dict values
            for v_key, v_value in value.items():
                self.update_config_impl(v_key, v_value, config[key])

    def format_and_save_config(self, config):
        config = config.copy()
        global_config = CommentedMap()
        plugins_config = CommentedMap()

        for key, value in config.items():
            if type(value) is not dict and type(value) is not CommentedMap:
                global_config[key] = value
            else:
                plugins_config[key] = value

        with open('./pybot.yaml', 'w') as outfile:
            yaml.dump(global_config, outfile, Dumper=yaml.RoundTripDumper)
            outfile.write('\n')
            yaml.dump(plugins_config, outfile, Dumper=yaml.RoundTripDumper)

        with open('./pybot.yaml', 'r+') as outfile:
            lines = outfile.readlines()
            outfile.truncate(0)
            for i, line in enumerate(lines):
                outfile.write(line)
                if line.strip() and line.startswith(' ') and i + 1 < len(lines) and lines[i + 1] and lines[i + 1][0].isalpha():
                    outfile.write('\n')

    def update_config(self):
        config = yaml.load(open("./pybot.yaml"), Loader=yaml.RoundTripLoader)
        for key, value in yaml.load(open("./pybot.template.yaml"), Loader=yaml.Loader).items():
            self.update_config_impl(key, value, config)

        if config == self.bot.config: return False

        self.bot.config = config
        self.format_and_save_config(config)
        self.logger.warning('config file updated')
        return True

    @command
    @admin
    def self_update(self, sender_nick, **kwargs):
        if not self.update_possible():
            self.logger.info(f'{sender_nick} asked for self-update, but there are local changes in {self.pybot_dir}')
            self.bot.say('local changes prevents me from update')
            return

        cmd = f'git -C {self.pybot_dir} pull'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()

        if process.returncode != 0:
            self.logger.error(
                f'{sender_nick} asked for self-update, but {cmd} returned {process.returncode} exit code')
            self.bot.say("cannot update, 'git pull' returns non-zero exit code")
        else:
            suffix = ''
            try:
                if self.update_config(): suffix = ', config file updated'
            except Exception as e:
                suffix = ', unable to update config file!'
                self.logger.warning(f'exception caught while updating config file: {e}')
                if self.bot.is_debug_mode_enabled(): raise

            self.logger.warning(f'{sender_nick} asked for self-update')
            self.bot.say(f'updated, now at "{self.get_current_head_pos()}"{suffix}')

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
        users = [user.lower() for user in users]

        with self.mutex:
            for x in self.commands_as_other_user_to_send:
                if x.hacked_nick.lower() not in users:
                    self.logger.info(f'removing {x.sender_nick} command ({x.raw_msg.arguments[0]}) as {x.hacked_nick}')
                    self.commands_as_other_user_to_send.remove(x)

    @command
    @admin
    def as_other_user(self, sender_nick, msg, raw_msg, **kwargs):
        if not msg: return
        hacked_nick = msg.split()[0]
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
