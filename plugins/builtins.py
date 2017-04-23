import os
import subprocess
import sys

from threading import Lock
from irc.client import NickMask
from collections import namedtuple

from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
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
                self.bot.send_response_to_channel('%s: %s' % (func_name, getattr(func, '__doc_string')))
            else:
                self.bot.send_response_to_channel('no help for %s' % func_name)

            self.logger.info('help of %s given for %s' % (func_name, sender_nick))

        else:
            commands = self.bot.get_commands_by_plugin()
            for p in commands:
                if commands[p]:
                    self.bot.send_response_to_channel('available commands for %s: %s' % (p, ', '.join(commands[p])))

            self.logger.info('help given for %s' % sender_nick)

    @command
    def source(self, sender_nick, **kwargs):
        src = r'https://github.com/pingwindyktator/pybot/tree/develop'
        self.logger.info('source %s given to %s' % (src, sender_nick))
        self.bot.send_response_to_channel('Patches are welcome! %s' % src)

    @command
    @admin
    def add_op(self, sender_nick, args, **kwargs):
        if len(args) == 0: return
        self.bot.ops.update(args)
        subreply = 'is now op' if len(args) == 1 else 'are now ops'
        self.bot.send_response_to_channel('%s %s' % (', '.join(args), subreply))
        self.logger.warning('%s added new ops: %s' % (sender_nick, args))

    @command
    @admin
    def rm_op(self, sender_nick, args, **kwargs):
        to_remove = [arg for arg in args if arg in self.bot.ops]
        if not to_remove: return
        for arg in to_remove:
            self.bot.ops.remove(arg)

        subreply = 'is no longer op' if len(to_remove) == 1 else 'are no longer ops'
        self.bot.send_response_to_channel('%s %s' % (to_remove, subreply))
        self.logger.warning('%s removed ops: %s' % (sender_nick, to_remove))

    @command
    @admin
    def ops(self, sender_nick, **kwargs):
        if len(self.bot.ops) == 0:
            subreply = 'no bot operators'
        elif len(self.bot.ops) == 1:
            subreply = 'bot operator:'
        else:
            subreply = 'bot operators:'

        self.bot.send_response_to_channel('%s %s' % (subreply, self.bot.ops))
        self.logger.info('%s asked for ops: %s' % (sender_nick, self.bot.ops))

    @command
    @admin
    def restart(self, sender_nick, **kwargs):
        args = sys.argv[:]

        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]

        self.logger.warning("re-spawning '%s' by %s" % (' '.join(args), sender_nick))
        os.chdir(os.getcwd())
        os.execv(sys.executable, args)

    def update_possible(self):
        cmd1 = 'git -C %s diff --exit-code' % self.pybot_dir  # unstaged changes
        process1 = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE)
        process1.wait(2)

        cmd2 = 'git -C %s cherry -v | wc -l' % self.pybot_dir  # not committed changes
        process2 = subprocess.Popen(cmd2, shell=True, stdout=subprocess.PIPE)
        out, err = process2.communicate()

        return process1.returncode == 0 and out == b'0\n'

    def get_current_head_pos(self):
        cmd = "git -C %s log --oneline -n 1 | sed 's/ /: /'" % self.pybot_dir
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()
        return ''.join([chr(x) for x in list(out)[:-1]])

    @command
    @admin
    def self_update(self, sender_nick, **kwargs):
        if not self.update_possible():
            self.logger.info(
                '%s asked for self-update, but there are local changes in %s' % (sender_nick, self.pybot_dir))
            self.bot.send_response_to_channel('local changes prevents me from update')
            return

        cmd = 'git -C %s pull' % self.pybot_dir
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()

        if process.returncode != 0:
            self.logger.error(
                '%s asked for self-update, but %s returned %s exit code' % (sender_nick, cmd, process.returncode))
            self.bot.send_response_to_channel("cannot update, 'git pull' returns non-zero exit code")
        else:
            self.logger.warning('%s asked for self-update' % sender_nick)
            self.bot.send_response_to_channel('updated, now at %s' % self.get_current_head_pos())

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
            '%s runs command (%s) as %s' % (args.sender_nick, hacked_raw_msg.arguments[0], args.hacked_nick))
        with self.mutex:
            self.commands_as_other_user_to_send.remove(args)

        self.bot.on_pubmsg(args.connection, hacked_raw_msg)

    def clean_commands_as_other_user_to_send(self):
        users = self.bot.channels[self.bot.channel].users()
        users = [user.lower() for user in users]

        with self.mutex:
            for x in self.commands_as_other_user_to_send:
                if x.hacked_nick.lower() not in users:
                    self.logger.info('removing %s command (%s) as %s' % (x.sender_nick, x.raw_msg.arguments[0], x.hacked_nick))
                    self.commands_as_other_user_to_send.remove(x)

    @command
    @admin
    def as_other_user(self, sender_nick, msg, raw_msg, **kwargs):
        if not msg: return
        hacked_nick = msg.split()[0]
        new_msg = msg[len(hacked_nick):].strip()
        raw_msg.arguments = (new_msg, raw_msg.arguments[1:])
        self.logger.info('%s queued command (%s) as %s' % (sender_nick, new_msg, hacked_nick))
        with self.mutex:
            self.commands_as_other_user_to_send.append(self.as_other_user_command(sender_nick, hacked_nick, self.bot.connection, raw_msg))

        # now we don't know ho to set raw_msg fields (user and host)
        # that's why we are queuing this call, then calling /whois hacked_user
        # when /whois response received, we've got needed user and host and we can do appropriate call
        self.clean_commands_as_other_user_to_send()
        self.bot.whois(hacked_nick)
