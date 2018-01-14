import re

from datetime import datetime
from datetime import timedelta
from plugin import *


class antispam(plugin):
    class msg_info:
        def __init__(self, last_msg_timestamp, msgs_in_row):
            self.last_msg_timestamp = last_msg_timestamp
            self.msgs_in_row = msgs_in_row

    def __init__(self, bot):
        super().__init__(bot)
        self.msg_infos = {}  # nickname -> msg_info
        self.long_msg_infos = {}  # nickname -> msg_info
        self.last_msg_author = None
        self.same_author_msgs_in_row = None
        self.last_msg_timestamp = None

    def on_pubmsg(self, raw_msg, source, msg, **kwargs):
        sender_nick = irc_nickname(source.nick)

        if self.is_spam(sender_nick, msg):
            if self.am_i_channel_operator():
                self.bot.kick(sender_nick, 'stop it!')
                self.logger.info(f'{sender_nick} kicked')
            else:
                self.logger.warning(f"{sender_nick} is possibly spamer, but I've no operator privileges to kick him :(")

    def is_spam(self, sender_nick, msg):
        # antispam checkers should be called even if user is whitelisted!
        result = False

        if self.config['kick_if_too_colorful_msgs'] and self.too_colorful_msg(sender_nick, msg): result = True
        if self.config['kick_if_too_many_msgs'] and self.too_many_msg(sender_nick, msg): result = True
        if self.config['kick_if_too_many_users_mentioned'] and self.too_many_users_mentioned(sender_nick, msg): result = True
        if self.config['kick_if_too_long_msgs'] and self.too_long_msgs(sender_nick, msg): result = True
        if self.config['kick_if_no_one_else_active'] and self.no_one_active(sender_nick, msg): result = True

        if self.is_whitelisted(sender_nick): result = False
        return result

    def is_whitelisted(self, sender_nick):
        sender_nick = irc_nickname(sender_nick)

        if sender_nick in self.bot.config['ops']: return True
        if sender_nick in self.bot.channel.mode_users['o']: return True
        if sender_nick in self.bot.channel.mode_users['+']: return True

        return False

    def am_i_channel_operator(self):
        return self.bot.get_nickname() in self.bot.channel.mode_users['o']

    def too_colorful_msg(self, sender_nick, msg):
        color_prefix = b'\x03' + r'[0-9]+'.encode()
        if isinstance(msg, str): msg = msg.encode()
        colors = len(re.findall(color_prefix, msg))

        return colors > 4

    def too_many_msg(self, sender_nick, msg):
        now = datetime.now()
        if sender_nick not in self.msg_infos:
            self.msg_infos[sender_nick] = self.msg_info(now, 1)
            return

        msg_info = self.msg_infos[sender_nick]

        if msg_info.last_msg_timestamp + timedelta(seconds=2) > now:
            msg_info.msgs_in_row += 1
        else:
            msg_info.msgs_in_row = 1

        msg_info.last_msg_timestamp = now
        self.msg_infos[sender_nick] = msg_info

        return msg_info.msgs_in_row > 5

    def too_many_users_mentioned(self, sender_nick, msg):
        users = self.bot.get_usernames_on_channel()
        count = 0

        for user in users:
            if re.findall(r'\b' + user + r'\b', msg, re.I):
                count += 1

        return count > 4

    def too_long_msgs(self, sender_nick, msg):
        if len(msg) < 300: return

        now = datetime.now()
        if sender_nick not in self.long_msg_infos:
            self.long_msg_infos[sender_nick] = self.msg_info(now, 1)
            return

        msg_info = self.long_msg_infos[sender_nick]

        if msg_info.last_msg_timestamp + timedelta(seconds=5) > now:
            msg_info.msgs_in_row += 1
        else:
            msg_info.msgs_in_row = 1

        msg_info.last_msg_timestamp = now
        self.long_msg_infos[sender_nick] = msg_info

        return msg_info.msgs_in_row > 2

    def no_one_active(self, sender_nick, msg):
        now = datetime.now()
        if self.last_msg_timestamp is None or self.last_msg_author is None:
            self.last_msg_timestamp = now
            self.last_msg_author = sender_nick
            self.same_author_msgs_in_row = 1
            return

        if sender_nick == self.last_msg_author and self.last_msg_timestamp + timedelta(minutes=60) > now:
            self.same_author_msgs_in_row += 1
        else:
            self.last_msg_author = sender_nick
            self.same_author_msgs_in_row = 1

        self.last_msg_timestamp = now
        return self.same_author_msgs_in_row > 9
