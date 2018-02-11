from datetime import timedelta
from threading import Timer

from plugin import *


class ignore(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.time_delta_regex = re.compile(r'([0-9]+[Hh])?\W*([0-9]+[Mm])?(.*)')
        self.ignore_timers = []

    def unload_plugin(self):
        for t in self.ignore_timers: t.cancel()

    @command
    @admin
    @doc("ignore <nickname>...: ignore user's messages")
    def ignore(self, sender_nick, args, **kwargs):
        to_ignore = [irc_nickname(arg) for arg in args if not self.bot.is_user_ignored(arg)]
        if not to_ignore:
            self.bot.say('no one to ignore')
            return

        for arg in to_ignore: self.bot.ignore_user(arg)

        reply = f'{to_ignore[0]} is now ignored' if len(to_ignore) == 1 else f'{to_ignore} are now ignored'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} ignored {to_ignore}')

    @command
    @admin
    @doc("ignore_for <nickname> <time>: ignore user's messages for <time> time. <time> should be %H %M  (eg.  1h 42m)")
    @doc("ignore_for <time> <nickname>: ignore user's messages for <time> time. <time> should be %H %M  (eg.  1h 42m)")
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

        if self.bot.is_user_ignored(nickname):
            self.bot.say(f'{nickname} is already ignored')
            return

        self.bot.ignore_user(nickname)
        self.logger.warning(f'{sender_nick} ignored {nickname} for {hours}H:{minutes}M')
        delta_time = timedelta(hours=hours, minutes=minutes).total_seconds()
        t = Timer(delta_time, self.unignore_user_timer_ended, kwargs={'nickname': nickname})
        self.ignore_timers.append(t)
        t.start()
        self.bot.say(f'{nickname} ignored for {time}')

    def unignore_user_timer_ended(self, nickname):
        self.logger.warning(f'time passed, {nickname} is no longer ignored')
        self.bot.unignore_user(nickname)

    @command
    @admin
    @doc("unignore <nickname>...: unignore user's messages")
    def unignore(self, sender_nick, args, **kwargs):
        to_unignore = [irc_nickname(arg) for arg in args if self.bot.is_user_ignored(arg)]
        if not to_unignore:
            self.bot.say('no one to unignore')
            return

        for arg in to_unignore: self.bot.unignore_user(arg)

        reply = f'{to_unignore[0]} is no longer ignored' if len(to_unignore) == 1 else f'{to_unignore} are no longer ignored'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} unignored {to_unignore}')

    @command
    @admin
    @doc('get ignored users')
    def ignored_users(self, sender_nick, **kwargs):
        ignored = self.bot.get_ignored_users()

        if len(ignored) == 0:
            self.bot.say('no ignored users')
        else:
            self.bot.say(f'ignored users: {", ".join(ignored)}')

        self.logger.info(f'{sender_nick} asked for ignored users: {ignored}')
