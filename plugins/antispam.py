import re

from datetime import datetime, timedelta
from plugin import *


class msg_info:
    def __init__(self, last_msg_timestamp, msgs_in_row):
        self.last_msg_timestamp = last_msg_timestamp
        self.msgs_in_row = msgs_in_row


class too_colorful_msg:
    def __init__(self, bot):
        self.bot = bot

    def reason(self):
        return 'too colorful msg'

    def check(self, sender_nick, msg):
        color_prefix = b'\x03' + r'[0-9]+'.encode()
        if isinstance(msg, str): msg = msg.encode()
        colors = len(re.findall(color_prefix, msg))

        return colors > 4


class too_many_msgs:
    def __init__(self, bot):
        self.bot = bot
        self.msg_infos = {}  # nickname -> msg_info

    def reason(self):
        return 'flood excess, too many msgs'

    def check(self, sender_nick, msg):
        now = datetime.now()
        if sender_nick not in self.msg_infos:
            self.msg_infos[sender_nick] = msg_info(now, 1)
            return False

        mi = self.msg_infos[sender_nick]

        if mi.last_msg_timestamp + timedelta(milliseconds=1200) > now:
            mi.msgs_in_row += 1
        else:
            mi.msgs_in_row = 1

        mi.last_msg_timestamp = now
        self.msg_infos[sender_nick] = mi
        return mi.msgs_in_row > 3


class too_many_users_mentioned:
    def __init__(self, bot):
        self.bot = bot

    def reason(self):
        return 'too many users mentioned'

    def check(self, sender_nick, msg):
        users = self.bot.get_usernames_on_channel()
        count = 0

        for user in users:
            if re.findall(r'\b' + user + r'\b', msg, re.I):
                count += 1

        return count > 4


class too_long_msgs:
    def __init__(self, bot):
        self.bot = bot
        self.msg_infos = {}  # nickname -> msg_info

    def reason(self):
        return 'too many long msgs'

    def check(self, sender_nick, msg):
        if len(msg) < 300: return False

        now = datetime.now()
        if sender_nick not in self.msg_infos:
            self.msg_infos[sender_nick] = msg_info(now, 1)
            return False

        mi = self.msg_infos[sender_nick]

        if mi.last_msg_timestamp + timedelta(seconds=5) > now:
            mi.msgs_in_row += 1
        else:
            mi.msgs_in_row = 1

        mi.last_msg_timestamp = now
        self.msg_infos[sender_nick] = mi
        return mi.msgs_in_row > 2


class same_msg_too_many_times:
    class same_msg_info:
        def __init__(self, sender_nick, count, last_msg_timestamp, msg):
            self.sender_nick = sender_nick
            self.count = count
            self.last_msg_timestamp = last_msg_timestamp
            self.msg = msg

    def __init__(self, bot):
        self.bot = bot
        self.same_msg_infos = {}  # nickname -> same_msg_info

    def reason(self):
        return 'same msg too many times'

    def check(self, sender_nick, msg):
        now = datetime.now()
        if sender_nick not in self.same_msg_infos:
            self.same_msg_infos[sender_nick] = self.same_msg_info(sender_nick, 1, now, msg)
            return False

        smi = self.same_msg_infos[sender_nick]

        if msg == smi.msg and smi.last_msg_timestamp + timedelta(minutes=60) > now:
            smi.count += 1
        else:
            smi.count = 1
            smi.msg = msg

        smi.last_msg_timestamp = now
        self.same_msg_infos[sender_nick] = smi
        return smi.count > 4


@doc('will detect and kick spamers')
class antispam(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.checkers = []
        if self.config['kick_if_too_colorful_msg']: self.checkers.append(too_colorful_msg(self.bot))
        if self.config['kick_if_too_many_msgs']: self.checkers.append(too_many_msgs(self.bot))
        if self.config['kick_if_too_many_users_mentioned']: self.checkers.append(too_many_users_mentioned(self.bot))
        if self.config['kick_if_too_long_msgs']: self.checkers.append(too_long_msgs(self.bot))
        if self.config['kick_if_same_msg_too_many_times']: self.checkers.append(same_msg_too_many_times(self.bot))
        checkers_names = [type(c).__name__ for c in self.checkers]
        self.logger.debug(f'antispam checkers registered: {checkers_names}')

    def on_pubmsg(self, raw_msg, source, msg, **kwargs):
        sender_nick = irc_nickname(source.nick)
        reason = self.get_kick_reason(sender_nick, msg)
        if not reason: return
        if self.is_whitelisted(sender_nick): return

        if self.am_i_channel_operator():
            self.bot.kick(sender_nick, 'stop it!')
            self.logger.warning(f'{sender_nick} kicked: {reason}')
        else:
            self.bot.say(f'{sender_nick}: stop spamming!')
            self.logger.warning(f"{sender_nick} is possibly spamer ({reason}), but I've no operator privileges to kick him :(")

    def get_kick_reason(self, sender_nick, msg):
        # antispam checkers should be called even if user is whitelisted!
        reason = None
        for checker in self.checkers:
            if checker.check(sender_nick, msg):
                reason = checker.reason()

        return reason

    @utils.timed_lru_cache(expiration=timedelta(seconds=5), typed=True)
    def is_whitelisted(self, sender_nick):
        if self.bot.is_user_op(sender_nick): return True
        if self.bot.get_channel().is_oper(sender_nick): return True
        if self.bot.get_channel().is_voiced(sender_nick): return True

        return False

    @utils.timed_lru_cache(expiration=timedelta(seconds=5))
    def am_i_channel_operator(self):
        return self.bot.get_channel().is_oper(self.bot.get_nickname())
