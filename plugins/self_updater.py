import subprocess
import os

from plugin import *


class self_updater(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)

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
