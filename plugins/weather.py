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
        result = ''

        if 'main' in weather_info and 'temp' in weather_info['main']:
            result = f'temperature: {self.colorize_temp(weather_info["main"]["temp"])} °C :: '

        if 'weather' in weather_info and len(weather_info['weather']) > 1 and 'description' in weather_info['weather'][0]:
            result = f'{result}conditions: {weather_info["weather"][0]["description"]} :: '

        if 'main' in weather_info and 'humidity' in weather_info['main']:
            result = f'{result}relative humidity: {weather_info["main"]["humidity"]}% :: '

        if 'wind' in weather_info and 'temp' in weather_info['wind'] and 'deg' in weather_info['wind']:
            result = f'{result}wind speed: {weather_info["wind"]["speed"]}mph {self.wind_degree_to_direction(weather_info["wind"]["deg"])}'

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
        directions = ['↑', '↗', '↗', '↗',
                      '→', '↘', '↘', '↘',
                      '↓', '↙', '↙', '↙',
                      '←', '↖', '↖', '↖']

        return directions[(deg % 16)]

    def colorize_temp(self, temp):
        temp = float(temp)
        if temp < 0:  return color.blue(temp)
        if temp < 10: return color.light_blue(temp)
        if temp < 15: return color.cyan(temp)
        if temp < 26: return color.yellow(temp)
        if temp < 30: return color.light_red(temp)
        return color.red(temp)
