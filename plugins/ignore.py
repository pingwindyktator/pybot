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

    def ignore_user_impl(self, username):
        if 'ignored_users' not in self.bot.config:
            self.bot.config['ignored_users'] = [username]
        else:
            self.bot.config['ignored_users'].append(username)

    @command
    @admin
    @doc("ignore <username>...: ignore user's messages")
    def ignore(self, sender_nick, args, **kwargs):
        if not args: return
        to_ignore = [irc_nickname(arg) for arg in args]
        for arg in to_ignore:
            self.ignore_user_impl(arg)

        reply = f'{to_ignore[0]} is now ignored' if len(to_ignore) == 1 else f'{to_ignore} are now ignored'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} ignored {to_ignore}')

    @command
    @admin
    @doc("ignore_for <username> <time>: ignore user's messages for <time> time. <time> should be %H %M  (eg.  1h 42m)")
    @doc("ignore_for <time> <username>: ignore user's messages for <time> time. <time> should be %H %M  (eg.  1h 42m)")
    def ignore_for(self, sender_nick, msg, **kwargs):
        if not msg: return
        return self.ignore_for_impl(sender_nick, msg)

    def ignore_for_impl(self, sender_nick, msg, reverted=False):
        username = irc_nickname(msg.split()[0].strip())
        time = msg[len(username):].strip()
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
                # trying to parse ignore_for <time> <username> instead of ignore_for <username> <time>
                return self.ignore_for_impl(sender_nick, f'{time} {username}', reverted=True)

        self.ignore_user_impl(username)
        self.logger.warning(f'{sender_nick} ignored {username} for {hours}H:{minutes}M')
        delta_time = timedelta(hours=hours, minutes=minutes).total_seconds()
        t = Timer(delta_time, self.unignore_user_timer_ended, kwargs={'username': username})
        self.ignore_timers.append(t)
        t.start()
        self.bot.say(f'{username} ignored for {time}')

    def unignore_user_impl(self, username):
        if 'ignored_users' not in self.bot.config: return
        self.bot.config['ignored_users'].remove(username)

    def unignore_user_timer_ended(self, username):
        if username in self.bot.config['ignored_users']:
            self.logger.warning(f'time passed, {username} is no longer ignored')
            self.unignore_user_impl(username)

    @command
    @admin
    @doc("unignore <username>...: unignore user's messages")
    def unignore(self, sender_nick, args, **kwargs):
        if 'ignored_users' not in self.bot.config: return
        to_unignore = [irc_nickname(arg) for arg in args]
        to_unignore = [arg for arg in to_unignore if arg in self.bot.config['ignored_users']]
        if not to_unignore: return
        for arg in to_unignore:
            self.unignore_user_impl(arg)

        reply = f'{to_unignore[0]} is no longer ignored' if len(to_unignore) == 1 else f'{to_unignore} are no longer ignored'
        self.bot.say(reply)
        self.logger.warning(f'{sender_nick} unignored {to_unignore}')

    @command
    @admin
    @doc('get ignored users')
    def ignored_users(self, sender_nick, **kwargs):
        ignored = self.bot.config['ignored_users'] if 'ignored_users' in self.bot.config else []

        if len(ignored) == 0:
            reply = 'no ignored users'
        else:
            reply = f'ignored users: {ignored}'

        self.bot.say(reply)
        self.logger.info(f'{sender_nick} asked for ignored users: {ignored}')
