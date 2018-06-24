import requests
import urllib.parse
import json

from datetime import timedelta
from plugin import *


class movie(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.omdbapi_url = r'http://www.omdbapi.com/?t=%s&apikey=%s'
        self.imdb_url = r'http://www.imdb.com/title/%s'

    @staticmethod
    def api_response_contains(response, key):
        if key not in response: return False
        if not response[key]: return False
        if isinstance(response[key], str):
            if response[key].upper() == 'N/A': return False
            if response[key].upper() == 'N/A.': return False

        return True

    @command
    @doc('movie <title>: get information about <title> movie')
    def movie(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked omdbapi about {msg}')
        response = self.get_movie_info(msg)
        if not response:
            self.bot.say_err()
            return

        prefix = self.build_prefix(response)
        ratings_str = ', '.join([f'{rating["Source"]}: {rating["Value"]}' for rating in response['Ratings']]) if self.api_response_contains(response, 'Ratings') else ''
        genre = f'{response["Genre"]}. ' if self.api_response_contains(response, 'Genre') else ''
        awards = f'{response["Awards"]} ' if self.api_response_contains(response, 'Awards') else ''
        url = f'({self.imdb_url % response["imdbID"]})' if self.api_response_contains(response, 'imdbID') else ''

        if genre or awards or url:
            self.bot.say(f'{prefix} {genre}{awards}{url}')

        if self.api_response_contains(response, 'Plot') and not self.bot.is_msg_too_long(f'{prefix} {response["Plot"]}'):
            self.bot.say(f'{prefix} {response["Plot"]}')

        if ratings_str: self.bot.say(f'{prefix} {ratings_str}')

    @command
    @doc('imdb <title>: get imdb URL to <title> movie')
    def imdb(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked omdbapi about imdb of {msg}')
        response = self.get_movie_info(msg)
        if not response or not self.api_response_contains(response, 'imdbID'):
            self.bot.say_err()
            return

        rating = f' ({response["imdbRating"]}/10 out of {response["imdbVotes"]} voters)' if self.api_response_contains(response, 'imdbRating') and 'imdbVotes' in response else ''
        self.bot.say(f'{self.build_prefix(response)} {self.imdb_url % response["imdbID"]}{rating}')

    @utils.timed_lru_cache(expiration=timedelta(hours=1), typed=True)
    def get_movie_info(self, movie):
        ask = urllib.parse.quote(movie)
        raw_response = requests.get(self.omdbapi_url % (ask, self.config['omdb_api_key'])).content.decode('utf-8')
        response = json.loads(raw_response)
        if response['Response'] == 'True' and self.api_response_contains(response, 'Title'): return response
        else:
            if 'not found' not in response['Error'].casefold():
                self.logger.warning(f'omdbapi returned error: {response["Error"]}')
                self.get_movie_info.do_not_cache()

            return None

    def build_prefix(self, movie_info):
        year = f' ({movie_info["Year"]})' if self.api_response_contains(movie_info, 'Year') else ''
        director = f' by {movie_info["Director"]}' if self.api_response_contains(movie_info, 'Director') else ''
        return color.orange(f'[{movie_info["Title"]}{year}{director}]')
