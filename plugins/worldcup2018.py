import json
import requests

from threading import Timer, RLock
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
        self.update_match_data_timer = utils.repeated_timer(timedelta(minutes=60).total_seconds(), self.update_match_data)
        self.update_match_data_timer.start()

    class match_desc:
        def __init__(self, home_team, away_team, date, goals_home_team, goals_away_team, status):
            self.home_team = home_team
            self.away_team = away_team
            self.date = date
            self.goals_home_team = goals_home_team
            self.goals_away_team = goals_away_team
            self.status = status

        def to_response(self):
            if self.status == 'future':
                return f'{color.cyan(self.home_team)} - {color.cyan(self.away_team)} starts at {color.green(self.date)}'

            elif self.status == 'completed':
                return f'{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}'

            elif self.status == 'in progress':
                return f'{color.cyan(self.home_team)} {self.goals_home_team} - {self.goals_away_team} {color.cyan(self.away_team)}'

    def unload_plugin(self):
        self.update_match_data_timer.cancel()
        for t in self.match_timers:
            t.cancel()

    @utils.timed_lru_cache(expiration=timedelta(minutes=3))
    def update_match_data(self):
        api_response = json.loads(requests.get(r'https://worldcup.sfg.io/matches').content.decode())
        now = datetime.now()
        match_timers = []
        next_matches_info = []
        last_matches_info = []
        in_play_matches_info = []

        for match in api_response:
            home_team = match['home_team_country']
            away_team = match['away_team_country']
            if not home_team or not away_team: continue
            goals_home_team = match['home_team']['goals'] if 'goals' in match['home_team'] else None
            goals_away_team = match['away_team']['goals'] if 'goals' in match['away_team'] else None

            assert match['datetime'][-1] == 'Z'
            match_date = datetime.strptime(match['datetime'][:-1], "%Y-%m-%dT%H:%M:%S")
            match_date = match_date.replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None)
            match_desc = self.match_desc(home_team, away_team, match_date, goals_home_team, goals_away_team, match['status'])

            remind_at = match_date - timedelta(minutes=15)
            if self.config['remind_before_match'] and remind_at > now and match['status'] == 'future':
                self.logger.debug(f'setting match reminder for {home_team} - {away_team}: {remind_at}')
                t = Timer((remind_at - now).total_seconds(), self.remind_upcoming_match, kwargs={'match_desc': match_desc})
                match_timers.append(t)
                t.start()

            if match['status'] == 'future':
                next_matches_info.append(match_desc)

            elif match['status'] == 'completed':
                last_matches_info.append(match_desc)

            elif match['status'] == 'in progress':
                in_play_matches_info.append(match_desc)

            else:
                self.logger.warning(f'something really wrong happen, unknown match status: {match["status"]}')

        next_matches_info.sort(key=lambda md: md.date)
        last_matches_info.sort(key=lambda md: md.date, reverse=True)

        with self.update_data_lock:
            for t in self.match_timers: t.cancel()
            self.match_timers = match_timers
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
