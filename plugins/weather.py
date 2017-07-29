import json
import urllib.parse
import requests

from plugin import *


class weather(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.api_url = r'http://api.openweathermap.org/data/2.5/weather?q=%s' \
                       r'&units=metric' \
                       r'&appid=%s'

    @doc('weather <location>: get current weather conditions in <location> from openweathermap (updated every ~2 hours)')
    @command
    def weather(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'getting weather in {msg} for {sender_nick}')
        weather_info = self.get_weather_info(msg)
        if not weather_info:
            self.bot.say(f'cannot obtain weather in {msg}')
            return

        prefix = color.orange(f'[Latest recorded weather for {weather_info["name"]}, {weather_info["sys"]["country"]}]')
        result = f'temperature: {weather_info["main"]["temp"]} °C ::'
        result = f'{result} conditions: {weather_info["weather"][0]["description"]} :: '
        result = f'{result} relative humidity: {weather_info["main"]["humidity"]}% :: '
        result = f'{result} wind speed: {weather_info["wind"]["speed"]}mph at {self.wind_degree_to_direction(weather_info["wind"]["deg"])}'
        self.bot.say(f'{prefix} {result}')

    def get_weather_info(self, city_name, national_chars=False):
        ask = urllib.parse.quote(city_name)
        raw_response = requests.get(self.api_url % (ask, self.config['api_key'])).content.decode('utf-8')
        response = json.loads(raw_response)
        if 'cod' not in response or response['cod'] != 200:
            self.logger.warning(f'openweathermap error: {raw_response}')
            return None

        # openweathermap behaves strange, sometimes it requires national characters and sometimes not
        if utils.remove_national_chars(response['name'].casefold()) != utils.remove_national_chars(city_name.casefold()):
            return self.get_weather_info(utils.remove_national_chars(city_name), True) if not national_chars else None
        else: return response

    def wind_degree_to_direction(self, deg):
        deg = int((deg / 22.5) + .5)
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        return directions[(deg % 16)]
