import re
from threading import Timer

from plugin import *
from datetime import datetime


class timer(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.time_regex = re.compile(r'^(([0-9]{1,2})-([0-9]{1,2})-([0-9]{4}) )?([0-9]{1,2}):([0-9]{1,2})$')
        self.to_notice = {}  # {timer_name -> nicknames}

    @command
    def set_timer(self, sender_nick, args, msg, **kwargs):
        if len(args) < 2: return
        name = args[0]
        time_str = msg[len(name):].strip()
        self.logger.info(f'{sender_nick} sets {name} timer to {time_str}')

        if name in self.to_notice:
            self.bot.say(f'{name} timer already exists')
            return

        reg_res = self.time_regex.findall(time_str)
        now = datetime.now()

        if not reg_res:
            self.bot.say('time should be YEAR-MONTH-DAY HOUR:MIN or HOUR:MIN formatted')
            return

        hour = f'{reg_res[0][4].zfill(2)}:{reg_res[0][5].zfill(2)}'
        if not reg_res[0][0]:
            day = now.strftime(r'%d-%m-%Y')
        else:
            day = f'{reg_res[0][1].zfill(2)}-{reg_res[0][2].zfill(2)}-{reg_res[0][3].zfill(2)}'

        run_at = datetime.strptime(f'{day} {hour}', r'%d-%m-%Y %H:%M')
        if run_at < now:
            self.bot.say(f'seems that {run_at} already passed')
            return

        delta_time = (run_at - now).seconds
        t = Timer(delta_time, self.notice, kwargs={'timer_name': name})
        self.to_notice[name] = {sender_nick}
        t.start()
        self.bot.say(f'{name} timer set to {run_at}')

    @command
    def timer_enroll(self, sender_nick, args, **kwargs):
        if not args: return
        name = args[0]
        self.logger.info(f'{sender_nick} enrolls to {name} timer')
        if name not in self.to_notice:
            self.bot.say(f'{name} timer does not exist')
            return

        self.to_notice[name].add(sender_nick)
        self.bot.say(f'enrolled to {name} timer')

    def notice(self, timer_name):
        self.bot.say(f"{timer_name}: {' '.join(self.to_notice[timer_name])}")
        del self.to_notice[timer_name]
