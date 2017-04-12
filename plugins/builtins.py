import inspect
import os
import subprocess
import sys

from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.pybot_dir = os.path.dirname(os.path.realpath(__file__))
        self.pybot_dir = os.path.abspath(os.path.join(self.pybot_dir, os.pardir))

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

    @command
    @admin
    def as_other_user(self, msg, connection, raw_msg):
        stack = inspect.stack()
        caller_frame = (stack[x] for x in range(0, len(stack))
                        if stack[x][3] == 'on_pubmsg' and stack[x][1].endswith('pybot.py')).__next__()
        raw_msg = caller_frame[0].f_locals['raw_msg']
        connection = caller_frame[0].f_locals['connection']
        self.bot.on_pubmsg(connection, raw_msg)
