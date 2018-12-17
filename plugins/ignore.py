import os
import sqlite3

from datetime import timedelta, datetime
from threading import Timer, Lock
from plugin import *


class ignore(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.time_delta_regex = re.compile(r'([0-9]+[Hh])?\W*([0-9]+[Mm])?(.*)')
        self.ignore_timers = []
        self.db_name = 'ignore'
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nickname TEXT primary key not null, timestamp TEXT)")  # nickname -> unignore_time
        self.db_mutex = Lock()
        self.restore_db_unignore_timers()

    def unload_plugin(self):
        for t in self.ignore_timers: t.cancel()

    def can_ignore_user(self, nickname):
        if self.bot.get_nickname() == nickname:
            return False, 'nice try'

        if self.bot.is_user_op(nickname):
            return False, f'{nickname} is a bot operator, I cannot ignore him'

        if self.bot.is_user_ignored(nickname):
            return False, f'{nickname} is already ignored'

        return True, None

    def restore_db_unignore_timers(self):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT nickname, timestamp FROM '{self.db_name}'")
            result = self.db_cursor.fetchall()

        for nickname, unignore_timestamp in result:
            delta_time = datetime.fromtimestamp(float(unignore_timestamp)) - datetime.now()
            self.logger.info(f'restored unignore timer for {nickname}: {delta_time}')
            if delta_time < timedelta():
                self.unignore_impl(nickname)

            t = Timer(delta_time.total_seconds(), self.unignore_user_timer_ended, kwargs={'nickname': nickname})
            self.ignore_timers.append(t)
            t.start()

    @command(admin=True)
    @command_alias('ignore_user')
    @doc("ignore <nickname>: ignore user's messages")
    def ignore(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        can_ignore, reason = self.can_ignore_user(nickname)
        if not can_ignore:
            self.bot.say(reason)
            return

        self.bot.ignore_user(nickname)
        self.bot.say(f'{nickname} is now ignored')
        self.logger.warning(f'{sender_nick} ignored {nickname}')

    @command(admin=True)
    @command_alias('ignore_user_for')
    @doc("""ignore_for <nickname> <time>: ignore user's messages for <time> time. <time> should be %H %M  (eg.  1h 42m)
            ignore_for <time> <nickname>: ignore user's messages for <time> time. <time> should be %H %M  (eg.  1h 42m)""")
    def ignore_for(self, sender_nick, msg, **kwargs):
        if not msg: return
        return self.ignore_for_impl(sender_nick, msg)

    def ignore_for_impl(self, sender_nick, msg, reverted=False):
        nickname = irc_nickname(msg.split()[0].strip())
        time = msg[len(nickname):].strip()
        if not time:
            self.bot.say('invalid format')
            return

        reg_res = self.time_delta_regex.findall(time)
        if not reg_res:
            self.bot.say('invalid format')
            return

        hours = int(reg_res[0][0][:-1]) if reg_res[0][0] else 0
        minutes = int(reg_res[0][1][:-1]) if reg_res[0][1] else 0
        if hours == 0 and minutes == 0:
            if reverted:
                self.bot.say('invalid format')
                return
            else:
                # trying to parse ignore_for <time> <nickname> instead of ignore_for <nickname> <time>
                return self.ignore_for_impl(sender_nick, f'{time} {nickname}', reverted=True)

        can_ignore, reason = self.can_ignore_user(nickname)
        if not can_ignore:
            self.bot.say(reason)
            return

        delta_time = timedelta(hours=hours, minutes=minutes)
        unignore_timestamp = (datetime.now() + delta_time).timestamp()
        with self.db_mutex:
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{self.db_name}' VALUES (?, ?)", (nickname, unignore_timestamp))
            self.db_connection.commit()

        self.bot.ignore_user(nickname)

        t = Timer(delta_time.total_seconds(), self.unignore_user_timer_ended, kwargs={'nickname': nickname})
        self.ignore_timers.append(t)
        t.start()

        self.logger.warning(f'{sender_nick} ignored {nickname} for {hours}H:{minutes}M')
        self.bot.say(f'{nickname} ignored for {time}')

    def unignore_user_timer_ended(self, nickname):
        self.logger.warning(f'time passed, {nickname} is no longer ignored')
        self.unignore_impl(nickname)

    def unignore_impl(self, nickname):
        self.bot.unignore_user(nickname)
        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (nickname,))
            self.db_connection.commit()

    @command(admin=True)
    @command_alias('unignore_user')
    @doc("unignore <nickname>: unignore user's messages")
    def unignore(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])

        if not self.bot.is_user_ignored(nickname):
            self.bot.say(f'{nickname} is not ignored')
            return

        self.unignore_impl(nickname)
        self.bot.say(f'{nickname} is no longer ignored')
        self.logger.warning(f'{sender_nick} unignored: {nickname}')

    @command(admin=True)
    @doc('get ignored users')
    def ignored_users(self, sender_nick, **kwargs):
        ignored = self.bot.get_ignored_users()

        if len(ignored) == 0:
            self.bot.say('no ignored users')
        else:
            self.bot.say(f'ignored users: {", ".join(ignored)}')

        self.logger.info(f'{sender_nick} asked for ignored users: {ignored}')
