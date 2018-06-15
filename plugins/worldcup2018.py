import json
import requests

from threading import Timer, RLock
from datetime import datetime, timedelta, timezone
from plugin import *

# TODO features wiki update
# TODO logging
# TODO wc_remind
# TODO docs


class worldcup2018(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.match_timers = []
        self.next_matches_info = []
        self.last_matches_info = []
        self.in_play_matches_info = []
        self.update_data_lock = RLock()
        self.update_match_timer = utils.repeated_timer(timedelta(minutes=60).total_seconds(), self.update_match_data)
        self.update_match_timer.start()

    class match_desc:
        def __init__(self, home_team, away_team, date, goals_home_team, goals_away_team, status):
            self.home_team = home_team
            self.away_team = away_team
            self.date = date
            self.goals_home_team = goals_home_team
            self.goals_away_team = goals_away_team
            self.status = status

        def to_response(self):
            if self.status == 'TIMED' or self.status == 'SCHEDULED':
                return f'{color.cyan(self.home_team)} - {color.cyan(self.away_team)} starts at {color.green(self.date)}'

            elif self.status == 'FINISHED':
                return f'{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}'

            elif self.status == 'IN_PLAY':
                return f'{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}'
            #     time_delta = datetime.now() - self.date
            #
            #     if time_delta < timedelta(minutes=0):  # before match
            #         time_delta = "0'"
            #
            #     elif timedelta(minutes=0) < time_delta <= timedelta(minutes=45):  # first half
            #         time_delta = int(time_delta.total_seconds() / 60)
            #         time_delta = f"{time_delta}'"
            #
            #     elif timedelta(minutes=45) < time_delta <= timedelta(minutes=60):  # half time break
            #         time_delta = "45'"
            #
            #     elif timedelta(minutes=60) < time_delta <= timedelta(minutes=105):  # second half
            #         time_delta -= timedelta(minutes=15)
            #         time_delta = int(time_delta.total_seconds() / 60)
            #         time_delta = f"{time_delta}'"
            #
            #     elif timedelta(minutes=105) < time_delta <= timedelta(minutes=110):  # full time break
            #         time_delta = "90'"
            #
            #     elif timedelta(minutes=110) < time_delta <= timedelta(minutes=140):  # extra time
            #         time_delta -= timedelta(minutes=20)
            #         time_delta = int(time_delta.total_seconds() / 60)
            #         time_delta = f"{time_delta}'"
            #
            #     elif time_delta > timedelta(minutes=140):  # after match
            #         time_delta = "120'"
            #
            #     return f"{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}, {time_delta}"

            else:
                raise RuntimeError('something really wrong happen, unknown match status')

    def unload_plugin(self):
        for t in self.match_timers:
            t.cancel()

    def get_api_response(self):
        return json.loads(requests.get(r'http://api.football-data.org/v1/competitions/467/fixtures').content.decode())

    def update_match_data(self):
        api_response = self.get_api_response()
        now = datetime.now()
        match_timers = []
        next_matches_info = []
        last_matches_info = []
        in_play_matches_info = []

        for match in api_response['fixtures']:
            home_team = match['homeTeamName']
            away_team = match['awayTeamName']
            goals_home_team = match['result']['goalsHomeTeam'] if match['result'] and 'goalsHomeTeam' in match['result'] else None
            goals_away_team = match['result']['goalsAwayTeam'] if match['result'] and 'goalsAwayTeam' in match['result'] else None

            assert match['date'][-1] == 'Z'
            match_date = datetime.strptime(match['date'][:-1], "%Y-%m-%dT%H:%M:%S")
            match_date = match_date.replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None)
            match_desc = self.match_desc(home_team, away_team, match_date, goals_home_team, goals_away_team, match['status'])

            remind_at = match_date - timedelta(minutes=15)
            if self.config['remind_before_match'] and remind_at > now and match['status'] == 'TIMED':
                self.logger.debug(f'setting match reminder for {home_team} - {away_team}: {remind_at}')
                t = Timer((remind_at - now).total_seconds(), self.remind_upcoming_match, kwargs={'match_desc': match_desc})
                match_timers.append(t)
                t.start()

            if match['status'] == 'TIMED':
                next_matches_info.append(match_desc)

            elif match['status'] == 'FINISHED':
                last_matches_info.append(match_desc)

            elif match['status'] == 'IN_PLAY':
                in_play_matches_info.append(match_desc)

        next_matches_info.sort(key=lambda md: md.date)
        last_matches_info.sort(key=lambda md: md.date, reverse=True)

        with self.update_data_lock:
            for t in self.match_timers: t.cancel()
            self.match_timers = match_timers
            self.next_matches_info = next_matches_info
            self.last_matches_info = last_matches_info
            self.in_play_matches_info = in_play_matches_info

    @command
    def wc_next(self, **kwargs):
        with self.update_data_lock:
            for md in self.next_matches_info[:3]:
                self.bot.say(md.to_response())

    @command
    def wc_last(self, **kwargs):
        with self.update_data_lock:
            for md in self.last_matches_info[:3]:
                self.bot.say(md.to_response())

    @command
    def wc_now(self, **kwargs):
        self.update_match_data()

        with self.update_data_lock:
            for md in self.in_play_matches_info:
                self.bot.say(md.to_response())

    def remind_upcoming_match(self, match_desc):
        prefix = '[2018 FIFA World Cup]'
        prefix = color.orange(prefix)
        self.bot.say(f'{prefix} {match_desc.to_response()}')
