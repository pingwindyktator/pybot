import requests
import urllib.parse
import json

from plugin import *


class movie(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.omdbapi_url = r'http://www.omdbapi.com/?t=%s&apikey=%s'
        self.imdb_url = r'http://www.imdb.com/title/%s'

    @command
    @doc('movie <title>: get information about <title> movie')
    def movie(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked omdbapi about {msg}')
        response = self.get_movie_info(msg)
        if not response:
            self.bot.say_err(msg)
            return

        prefix = self.build_prefix(response)
        ratings_str = ', '.join([f'{rating["Source"]}: {rating["Value"]}' for rating in response['Ratings']]) if 'Ratings' in response else ''
        genre = f'{response["Genre"]}. ' if 'Genre' in response else ''
        awards = response['Awards'] if 'Awards' in response else ''

        self.bot.say(f'{prefix} {genre}{awards}')

        if 'Plot' in response and not self.bot.is_msg_too_long(f'{prefix} {response["Plot"]}'):
            self.bot.say(f'{prefix} {response["Plot"]}')

        if ratings_str: self.bot.say(f'{prefix} {ratings_str}')
        if 'imdbID' in response: self.bot.say(f'{prefix} {self.imdb_url % response["imdbID"]}')

    @command
    @doc('imdb <tutle>: get imdb URL to <title> movie')
    def imdb(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked omdbapi about imdb of {msg}')
        response = self.get_movie_info(msg)
        if not response or 'imdbID' not in response:
            self.bot.say_err(msg)
            return

        rating = f' ({response["imdbRating"]} out of {response["imdbVotes"]} voters)' if 'imdbRating' in response and 'imdbVotes' in response else ''
        self.bot.say(f'{self.build_prefix(response)} {self.imdb_url % response["imdbID"]}{rating}')

    def get_movie_info(self, movie):
        ask = urllib.parse.quote(movie)
        raw_response = requests.get(self.omdbapi_url % (ask, self.config['api_key'])).content.decode('utf-8')
        response = json.loads(raw_response)
        return response if response['Response'] == 'True' and 'Title' in response else None

    def build_prefix(self, movie_info):
        year = f' ({movie_info["Year"]})' if 'Year' in movie_info else ''
        director = f' by {movie_info["Director"]}' if 'Director' in movie_info else ''
        return f'[{movie_info["Title"]}{year}{director}]'
