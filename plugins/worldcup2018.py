import json
import requests

from threading import Timer, RLock, Lock
from datetime import datetime, timedelta, timezone
from plugin import *


class worldcup2018(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.match_timers = []
        self.next_matches_info = []
        self.last_matches_info = []
        self.in_play_matches_info = []
        self.update_data_lock = RLock()
        self.update_timers_lock = Lock()
        self.update_match_data_timer = utils.repeated_timer(timedelta(minutes=1).total_seconds(), self.update_match_data)
        self.update_match_data_timer.start()
        self.update_match_timers_timer = utils.repeated_timer(timedelta(days=1).total_seconds(), self.update_match_timers)
        self.update_match_timers_timer.start()

    class match_desc:
        def __init__(self, home_team, away_team, date, goals_home_team, goals_away_team, status, city, stadium, time, id):
            self.home_team = home_team
            self.away_team = away_team
            self.date = date
            self.goals_home_team = goals_home_team
            self.goals_away_team = goals_away_team
            self.status = status
            self.city = city
            self.stadium = stadium
            self.time = time
            self.id = id

        def to_response(self):
            if self.status == 'future':
                return f'{color.cyan(self.home_team)} - {color.cyan(self.away_team)} starts at {color.green(self.date)}, {self.stadium}, {self.city}'

            elif self.status == 'completed':
                return f'{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}, {self.stadium}, {self.city}'

            elif self.status == 'in progress':
                return f'{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}, {self.time}'

        @staticmethod
        def from_api_response(match):
            if match['status'] not in ['future', 'completed', 'in progress']:
                raise Exception(f'unknown match status: {match["status"]}')

            if match['datetime'][-1] != 'Z':
                raise Exception(f'invalid match datetime: {match["datetime"]}')

            goals_home_team = match['home_team']['goals'] if 'goals' in match['home_team'] else None
            goals_away_team = match['away_team']['goals'] if 'goals' in match['away_team'] else None
            match_date = worldcup2018.match_datetime_to_local(match['datetime'])
            return worldcup2018.match_desc(match['home_team_country'], match['away_team_country'], match_date, goals_home_team,
                                           goals_away_team, match['status'], match['venue'], match['location'], match['time'], match['fifa_id'])

    @staticmethod
    def match_datetime_to_local(match_datetime):
        assert match_datetime[-1] == 'Z'
        return datetime.strptime(match_datetime[:-1], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None)

    def unload_plugin(self):
        self.update_match_data_timer.cancel()
        self.update_match_timers_timer.cancel()
        for t in self.match_timers: t.cancel()

    def get_api_response(self):
        return json.loads(requests.get(r'https://worldcup.sfg.io/matches').content.decode())

    def update_match_timers(self):
        if not self.config['remind_before_match']: return
        now = datetime.now()
        api_response = self.get_api_response()
        match_timers = []

        for match in api_response:
            match_desc = self.match_desc.from_api_response(match)
            remind_at = match_desc.date - timedelta(minutes=15)

            if remind_at > now and match_desc.status == 'future':
                self.logger.debug(f'setting match reminder for {match_desc.home_team} - {match_desc.away_team}: {remind_at}')
                t = Timer((remind_at - now).total_seconds(), self.remind_upcoming_match, kwargs={'match_desc': match_desc})
                match_timers.append(t)
                t.start()

        with self.update_timers_lock:
            for t in self.match_timers: t.cancel()
            self.match_timers = match_timers

    def update_match_data(self):
        api_response = self.get_api_response()
        next_matches_info = []
        last_matches_info = []
        in_play_matches_info = []

        for match in api_response:
            try:
                match_desc = self.match_desc.from_api_response(match)
            except Exception as e:
                self.logger.warning(f'cannot parse api response: {type(e).__name__}: {e}')
                continue

            if match_desc.status == 'future':
                next_matches_info.append(match_desc)
            elif match_desc.status == 'completed':
                last_matches_info.append(match_desc)
            elif match_desc.status == 'in progress':
                in_play_matches_info.append(match_desc)

        next_matches_info.sort(key=lambda md: md.date)
        last_matches_info.sort(key=lambda md: md.date, reverse=True)

        with self.update_data_lock:
            self.next_matches_info = next_matches_info
            self.last_matches_info = last_matches_info
            self.in_play_matches_info = in_play_matches_info

    @command
    @doc('get upcoming 2018 FIFA World Cup matches')
    def wc_next(self, sender_nick, **kwargs):
        self.logger.info(f'{sender_nick} asks about next matches')
        self.update_match_data()

        with self.update_data_lock:
            for md in self.next_matches_info[:3]:
                self.bot.say(md.to_response())

    @command
    @doc('get last 2018 FIFA World Cup matches')
    def wc_last(self, sender_nick, **kwargs):
        self.logger.info(f'{sender_nick} asks about last matches')

        with self.update_data_lock:
            for md in self.last_matches_info[:3]:
                self.bot.say(md.to_response())

    @command
    @doc('get 2018 FIFA World Cup matches in play')
    def wc_now(self, sender_nick, **kwargs):
        self.logger.info(f'{sender_nick} asks about in play matches')
        self.update_match_data()

        with self.update_data_lock:
            if not self.in_play_matches_info:
                self.bot.say('no matches in progress, last ones are:')
                for md in self.last_matches_info[:3]:
                    self.bot.say(md.to_response())

            else:
                for md in self.in_play_matches_info:
                    self.bot.say(md.to_response())

    def remind_upcoming_match(self, match_desc):
        prefix = '[2018 FIFA World Cup]'
        prefix = color.orange(prefix)
        self.bot.say(f'{prefix} {match_desc.to_response()}')
