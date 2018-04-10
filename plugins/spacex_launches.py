import json
import os
import requests
import sqlite3

from datetime import datetime, timedelta
from threading import Lock, Timer
from plugin import *

# TODO if starts for < 20 minutes...
class spacex_launches(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = self.bot.get_server_name()
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nickname TEXT primary key not null)")
        self.db_mutex = Lock()
        self.upcoming_launches_timers = {}  # {flight_id -> upcoming_launch_info}
        self.check_upcoming_launches_timer = utils.repeated_timer(timedelta(minutes=self.config['update_every_min']).total_seconds(), self.check_upcoming_launches)
        self.check_upcoming_launches_timer.start()

    class upcoming_launch_info:
        def __init__(self, launch_datetime, timers):
            self.launch_datetime = launch_datetime
            self.timers = timers

    def unload_plugin(self):
        for info in self.upcoming_launches_timers.values():
            for timer in info.timers:
                timer.cancel()

        self.check_upcoming_launches_timer.cancel()

    def get_upcoming_launches(self):
        upcoming_api_uri = r'https://api.spacexdata.com/v2/launches/upcoming'
        raw_response = requests.get(upcoming_api_uri).content.decode('utf-8')
        response = json.loads(raw_response)
        return response

    def get_launch_by_id(self, flight_id):
        flight_api_uri = r'https://api.spacexdata.com/v2/launches/all?flight_number=%s'
        raw_response = requests.get(flight_api_uri % flight_id).content.decode('utf-8')
        return json.loads(raw_response)[0]

    def get_latest_launch(self):
        latest_api_uri = r'https://api.spacexdata.com/v2/launches/latest'
        raw_response = requests.get(latest_api_uri).content.decode('utf-8')
        return json.loads(raw_response)

    def check_upcoming_launches(self):
        self.logger.debug('checking upcoming launches...')
        next_launches = self.get_upcoming_launches()

        for next_launch in next_launches:
            self.check_upcoming_launch(next_launch)

    def check_upcoming_launch(self, next_launch):
        flight_id = next_launch['flight_number']
        next_launch_time = datetime.fromtimestamp(next_launch['launch_date_unix']) if next_launch['launch_date_unix'] else None

        if flight_id in self.upcoming_launches_timers:
            if self.upcoming_launches_timers[flight_id].launch_datetime != next_launch_time:
                old_launch_time = self.upcoming_launches_timers[flight_id].launch_datetime
                self.inform_postponed_launch(next_launch, old_launch_time)
                self.logger.debug(f'canceling timers for {flight_id}')
                for timer in self.upcoming_launches_timers[flight_id].timers: timer.cancel()
                del self.upcoming_launches_timers[flight_id]
            else:
                self.logger.debug(f'timers for {flight_id} already set')
                return

        self.logger.info(f'setting launch time for {flight_id}: {next_launch_time}')
        self.upcoming_launches_timers[flight_id] = self.upcoming_launch_info(next_launch_time, [])

        if next_launch_time:
            self.add_reminder_at(next_launch_time - timedelta(hours=24), flight_id, next_launch_time)
            self.add_reminder_at(next_launch_time - timedelta(hours=1), flight_id, next_launch_time)
            self.add_reminder_at(next_launch_time - timedelta(minutes=20), flight_id, next_launch_time)

    def add_reminder_at(self, time, flight_id, launch_time):
        now = datetime.now()
        if time < now: return

        timer = Timer((time - now).total_seconds(), self.remind_upcoming_launch, kwargs={'flight_id': flight_id})
        self.upcoming_launches_timers[flight_id].timers.append(timer)
        self.upcoming_launches_timers[flight_id].launch_datetime = launch_time
        timer.start()
        self.logger.info(f'reminder at {time} set for upcoming launch: {flight_id}')

    def inform_postponed_launch(self, launch, old_launch_time):
        users_to_call = self.get_users_to_call()
        flight_id = launch['flight_number']
        new_launch_time = datetime.fromtimestamp(launch['launch_date_unix']) if launch['launch_date_unix'] else None
        assert new_launch_time != old_launch_time

        old_time_str = color.green(old_launch_time.strftime('%Y-%m-%d %H:%M')) + utils.get_str_utc_offset() if old_launch_time else '<unknown>'
        new_time_str = color.green(new_launch_time.strftime('%Y-%m-%d %H:%M')) + utils.get_str_utc_offset() if new_launch_time else '<unknown>'
        self.logger.info(f'launch {flight_id} was just postponed: {old_time_str} -> {new_time_str}')

        if self.config['inform_about_postponed_launches'] and users_to_call:
            if self.config['call_users_for_postponed_launches']: prefix = ', '.join(users_to_call) + ': '
            else: prefix = ''

            rocket_name = color.cyan(launch['rocket']['rocket_name'])
            flight_id_str = color.orange(flight_id)

            suffix = f'{rocket_name} launch {flight_id_str} was just postponed: {old_time_str} -> {new_time_str}'
            self.bot.say(f'{prefix}{suffix}')
            self.bot.say(self.get_launch_info_str(launch))

    def remind_upcoming_launch(self, flight_id):
        self.logger.info(f'reminding about next upcoming launch: {flight_id}')
        to_call = self.get_users_to_call()
        if not to_call: return

        launch = self.get_launch_by_id(flight_id)
        launch_time = datetime.fromtimestamp(launch['launch_date_unix']) if launch['launch_date_unix'] else None

        if launch['launch_success'] is not None \
                or not launch['launch_date_unix'] \
                or (launch_time < datetime.now()) \
                or flight_id not in self.upcoming_launches_timers \
                or launch_time != self.upcoming_launches_timers[flight_id].launch_datetime:
            self.logger.warning(f'launch {flight_id} probably canceled / postponed, skipping...')
            return

        self.bot.say(', '.join(to_call))  # TODO if too long...
        self.bot.say(self.get_launch_info_str(launch))

    @command
    @doc('get upcoming SpaceX launches info')
    def spacex_next(self, sender_nick, **kwargs):
        self.logger.info(f'{sender_nick} wants spacex upcoming launch')
        launches = self.get_upcoming_launches()[0:self.config['next_launches']]

        if not launches:
            self.bot.say('no scheduled launches')
            return

        for launch in launches:
            self.bot.say(self.get_launch_info_str(launch))

    def get_launch_info_str(self, launch):
        if not launch['launch_date_unix']:
            past = False
            include_video_uri = False
            time = ''
        else:
            past = datetime.fromtimestamp(launch['launch_date_unix']) < datetime.now()
            include_video_uri = (datetime.fromtimestamp(launch['launch_date_unix']) < datetime.now() + timedelta(hours=2)) or (past and launch['links']['video_link'])
            time = datetime.fromtimestamp(launch['launch_date_unix'])
            time = ' on ' + color.green(time.strftime('%Y-%m-%d')) + ' at ' + color.green(time.strftime('%H:%M')) + utils.get_str_utc_offset()

        flight_id = color.orange(f'[{launch["flight_number"]}]')
        rocket_name = color.cyan(launch['rocket']['rocket_name'])
        reused = launch['reuse']['core'] or launch['reuse']['side_core1'] or launch['reuse']['side_core2']
        reused = 'Reused' if reused else 'Unused'
        launch_site = launch['launch_site']['site_name']
        uri = launch['links']['video_link'] if launch['links']['video_link'] else r'http://www.spacex.com/webcast'

        try:
            payload_weight = sum([payload['payload_mass_kg'] for payload in launch['rocket']['second_stage']['payloads']])
            payload_weight = f' with {payload_weight}kg payload'
        except (KeyError, TypeError): payload_weight = ''
        try:
            orbits = [payload['orbit'] for payload in launch['rocket']['second_stage']['payloads']]
            orbits = ', '.join(list(set(orbits)))
            orbits = f' to {orbits}'
        except (KeyError, TypeError): orbits = ''
        payload_info = f'{payload_weight}{orbits}'

        result = f'{flight_id} ' if self.config['include_flight_id'] else ''
        result += f'{reused} {rocket_name} {"launched" if past else "launches"}{time} from {launch_site}{payload_info}'
        result += f': {uri}' if include_video_uri else ''
        return result

    @command
    @doc('get last SpaceX launch info')
    def spacex_last(self, sender_nick, **kwargs):
        self.logger.info(f'{sender_nick} wants spacex latest launch')
        latest_launch = self.get_latest_launch()

        prefix = '[LAUNCH SUCCESS] ' if latest_launch['launch_success'] else '[LAUNCH FAIL] '
        land_success = [c['land_success'] for c in latest_launch['rocket']['first_stage']['cores']]

        if land_success.count(None) == len(land_success):
            prefix += '[NO LANDING ATTEMPT]'
        else:
            land_success = list(filter(lambda l: l is not None, land_success))
            if True in land_success and False in land_success: prefix += '[LANDING PARTIALLY SUCCESS]'
            elif True in land_success: prefix += '[LANDING SUCCESS]'
            else: prefix += '[LANDING FAIL]'

        prefix = color.orange(prefix)
        if self.config['include_details'] and latest_launch['details']:
            self.bot.say(self.get_launch_info_str(latest_launch))
            self.bot.say(f'{prefix} {latest_launch["details"]}')
        else:
            self.bot.say(f'{prefix} {self.get_launch_info_str(latest_launch)}')

    def get_users_to_call(self):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT nickname FROM '{self.db_name}'")
            db_result = self.db_cursor.fetchall()

        db_result = [irc_nickname(n[0]) for n in db_result]
        on_channel = self.bot.get_usernames_on_channel()
        result = []

        for saved in db_result:
            for present in on_channel:
                if saved.casefold() in present.casefold():
                    result.append(present)
                    break

        return result

    @command
    @doc('will keep you updated on all upcoming SpaceX launches')
    def spacex_remind(self, sender_nick, **kwargs):
        with self.db_mutex:
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{self.db_name}' VALUES (?)", (sender_nick.casefold(),))
            self.db_connection.commit()

        self.bot.say_ok()

    @command
    @doc('stop informing me about upcoming SpaceX launches')
    def spacex_rm_remind(self, sender_nick, **kwargs):
        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (sender_nick.casefold(),))
            self.db_connection.commit()

        self.bot.say_ok()
