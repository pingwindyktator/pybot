import re
import uuid

from threading import Timer
from plugin import *
from datetime import datetime
from datetime import timedelta


class timer(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.time_regex = re.compile(r'^(([0-9]{1,2})-([0-9]{1,2})-([0-9]{4}) )?([0-9]{1,2}):([0-9]{1,2})(.*)')
        self.delta_regex = re.compile(r'([0-9]+[Hh])?\W*([0-9]+[Mm])?(.*)')
        self.to_notice = {}  # {timer_id -> (sender_nick, msg)}

    @command
    @doc('''
    set_timer <time> <msg>: sets timer to <time>. <time> can be  %d-%m-%Y %H:%M  or  %H:%M or  %Hh %Mm  (eg. '2017-12-1 13:14' / '13:14' or '3h 2m')
    ''')
    def set_timer(self, sender_nick, msg, **kwargs):
        now = datetime.now()
        run_at, msg = self.prepare_run_time(msg, now)
        if not run_at:
            self.bot.say('possibly bad time format')
            return

        self.logger.info(f'{sender_nick} sets timer to {run_at}: {msg}')

        if run_at < now:
            self.bot.say(f'seems that {run_at} already passed')
            return

        if not msg: msg = 'time passed!'
        delta_time = (run_at - now).seconds
        timer_id = uuid.uuid4()
        t = Timer(delta_time, self.notice, kwargs={'timer_id': timer_id})
        self.to_notice[timer_id] = (sender_nick, msg,)
        t.start()
        self.bot.say(f'timer set to {run_at}')

    def notice(self, timer_id):
        self.bot.say(f'{self.to_notice[timer_id][0]}: {self.to_notice[timer_id][1]}')
        del self.to_notice[timer_id]

    def prepare_run_time(self, msg, now):
        try:
            return self.prepare_run_time_impl(msg, now)
        except Exception as e:
            self.logger.info(f'possibly invalid time: {e}')
            return None, None

    def prepare_run_time_impl(self, msg, now):
        time_reg_res = self.time_regex.findall(msg)
        delta_reg_res = self.delta_regex.findall(msg)

        if time_reg_res:
            hour = f'{time_reg_res[0][4].zfill(2)}:{time_reg_res[0][5].zfill(2)}'
            if not time_reg_res[0][0]:
                day = now.strftime(r'%d-%m-%Y')
            else:
                day = f'{time_reg_res[0][1].zfill(2)}-{time_reg_res[0][2].zfill(2)}-{time_reg_res[0][3].zfill(2)}'
            run_at = datetime.strptime(f'{day} {hour}', r'%d-%m-%Y %H:%M')
            msg = time_reg_res[0][6].strip()
            return run_at, msg

        elif delta_reg_res:
            hour_delta = int(delta_reg_res[0][0][:-1]) if delta_reg_res[0][0] else 0
            minute_delta = int(delta_reg_res[0][1][:-1]) if delta_reg_res[0][1] else 0
            if hour_delta == 0 and minute_delta == 0: return None, None
            msg = delta_reg_res[0][2]
            run_at = now + timedelta(hours=hour_delta, minutes=minute_delta)
            return run_at, msg
        else: return None, None
