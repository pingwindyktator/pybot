import json
import requests

from threading import Timer
from datetime import datetime, timedelta, timezone
from plugin import *


class worldcup2018(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.match_timers = []
        self.next_matches_info = []
        self.update_match_timer = utils.repeated_timer(timedelta(minutes=60).total_seconds(), self.update_match_timers)
        self.update_match_timer.start()

    class match_desc:
        def __init__(self, home_team, away_team, date):
            self.home_team = home_team
            self.away_team = away_team
            self.date = date

        def to_response(self):
            return f'{color.green(self.home_team)} - {color.green(self.away_team)} starts at {self.date}'

    def unload_plugin(self):
        for t in self.match_timers:
            t.cancel()

    def get_api_response(self):
        return json.loads(requests.get(r'http://api.football-data.org/v1/competitions/467/fixtures').content.decode())

    def update_match_timers(self):
        for t in self.match_timers: t.cancel()
        self.match_timers.clear()
        self.next_matches_info.clear()

        api_response = self.get_api_response()
        now = datetime.now()

        for match in api_response['fixtures']:
            home_team = match['homeTeamName']
            away_team = match['awayTeamName']

            assert match['date'][-1] == 'Z'
            match_date = datetime.strptime(match['date'][:-1], "%Y-%m-%dT%H:%M:%S")
            match_date = match_date.replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None)
            match_desc = self.match_desc(home_team, away_team, match_date)

            remind_at = match_date - timedelta(minutes=15)
            if self.config['remind_before_match'] and remind_at > now and match['status'] == 'TIMED':
                self.logger.debug(f'setting match reminder for {home_team} - {away_team}: {remind_at}')
                t = Timer((remind_at - now).total_seconds(), self.remind_upcoming_match, kwargs={'match_desc': match_desc})
                self.match_timers.append(t)
                t.start()

            if match['status'] == 'TIMED':
                self.next_matches_info.append(match_desc)

        self.next_matches_info.sort(key=lambda md: md.date)

    @command
    def wc_next(self, **kwargs):
        for md in self.next_matches_info[:3]:
            self.bot.say(md.to_response())

    def remind_upcoming_match(self, match_desc):
        prefix = '[2018 FIFA World Cup]'
        prefix = color.blue(prefix)
        self.bot.say(f'{prefix} {match_desc.to_response()}')
