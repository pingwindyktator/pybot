import os
import subprocess
import sys

from plugin import *


class builtins(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

    @command
    def help(self, sender_nick, args):
        commands = self.bot.get_commands_by_plugin()
        for p in commands:
            if commands[p]:  # != []
                self.bot.send_response_to_channel('available commands for %s: %s' % (p, ', '.join(commands[p])))

        self.logger.info('help given for %s' % sender_nick)

    @command
    def source(self, sender_nick, args):
        src = r'https://github.com/pingwindyktator/pybot'
        self.logger.info('source %s given to %s' % (src, sender_nick))
        self.bot.send_response_to_channel('Patches are welcome! %s' % src)

    @command
    @admin
    def add_op(self, sender_nick, args):
        if len(args) == 0: return
        self.bot.ops.update(args)
        subreply = 'is now op' if len(args) == 1 else 'are now ops'
        self.bot.send_response_to_channel('%s %s' % (', '.join(args), subreply))
        self.logger.warn('%s added new ops: %s' % (sender_nick, args))

    @command
    @admin
    def rm_op(self, sender_nick, args):
        to_remove = [arg for arg in args if arg in self.bot.ops]
        if not to_remove: return
        for arg in to_remove:
            self.bot.ops.remove(arg)

        subreply = 'is no longer op' if len(to_remove) == 1 else 'are no longer ops'
        self.bot.send_response_to_channel('%s %s' % (to_remove, subreply))
        self.logger.warn('%s removed ops: %s' % (sender_nick, to_remove))

    @command
    @admin
    def ops(self, sender_nick, args):
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
    def restart(self, sender_nick, args):
        args = sys.argv[:]

        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]

        self.logger.warn("re-spawning '%s' by %s" % (' '.join(args), sender_nick))
        os.chdir(os.getcwd())
        os.execv(sys.executable, args)

    @command
    @admin
    def self_update(self, sender_nick, args):
        dir_path_ = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.abspath(os.path.join(dir_path_, os.pardir))

        cmd1 = 'git -C %s diff --exit-code' % dir_path  # unstaged changes
        process1 = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE)
        process1.wait(2)

        cmd2 = 'git -C %s cherry -v | wc -l' % dir_path  # not committed changes
        process2 = subprocess.Popen(cmd2, shell=True, stdout=subprocess.PIPE)
        out, err = process2.communicate()

        if process1.returncode != 0 or out != b'0\n':
            self.logger.info('%s asked for self-update, but there are local changes in %s' % (sender_nick, dir_path))
            self.bot.send_response_to_channel('local changes prevents me from update')
            return

        cmd = 'git -C %s pull' % dir_path
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()

        if process.returncode != 0:
            self.logger.error('%s asked for self-update, but %s returned %s exit code' % (sender_nick, cmd, process.returncode))
            self.bot.send_response_to_channel("cannot update, 'git pull' returns non-zero exit code")
        else:
            self.logger.warn('%s asked for self-update' % sender_nick)
            self.bot.send_response_to_channel('updated!')
