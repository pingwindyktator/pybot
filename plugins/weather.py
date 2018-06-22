import json
import urllib.parse
import datetime
import requests

from plugin import *


class weather(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.weather_url = r'http://api.openweathermap.org/data/2.5/weather?q=%s' \
                           r'&units=metric' \
                           r'&appid=%s'

        self.forecast_url = r'http://api.openweathermap.org/data/2.5/forecast?q=%s' \
                            r'&units=metric' \
                            r'&appid=%s'

    class forecast_info:
        def __init__(self, max_temp, min_temp, avg_wind_speed, avg_humidity, conditions):
            self.max_temp = max_temp
            self.min_temp = min_temp
            self.avg_wind_speed = avg_wind_speed
            self.avg_humidity = avg_humidity
            self.conditions = conditions

    @doc('weather <location>: get current weather conditions in <location> from openweathermap (updated every ~2 hours)')
    @command
    def weather(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'getting weather in {msg} for {sender_nick}')
        weather_info = self.get_weather_info(msg)
        if not weather_info:
            self.bot.say_err()
            return

        prefix = color.orange(f'[Latest recorded weather for {weather_info["name"]}, {weather_info["sys"]["country"]}]')
        results = []

        if 'main' in weather_info and 'temp' in weather_info['main']:
            results.append(f'{self.colorize_temp(weather_info["main"]["temp"])} °C')

        if 'weather' in weather_info and len(weather_info['weather']) > 0:
            results.append(f'{weather_info["weather"][0]["description"]}')

        if 'main' in weather_info and 'humidity' in weather_info['main']:
            results.append(f'relative humidity: {weather_info["main"]["humidity"]}%')

        if 'wind' in weather_info and 'speed' in weather_info['wind'] and 'deg' in weather_info['wind']:
            results.append(f'wind speed: {weather_info["wind"]["speed"]}mps {self.wind_degree_to_direction(weather_info["wind"]["deg"])}')

        self.bot.say(f'{prefix} {" :: ".join(results)}')

    @doc('forecast <location>: get weather forecast in <location> from openweathermap')
    @command
    def forecast(self, sender_nick, msg, **kwargs):
        if not msg: return
        self.logger.info(f'getting weather forecast in {msg} for {sender_nick}')
        weather_info = self.get_forecast_info(msg)
        if not weather_info:
            self.bot.say_err()
            return

        forecasts = {
            'today': self.parse_forecast(weather_info, 0),
            'next night': self.parse_forecast(weather_info, 1, night=True),
            'tomorrow': self.parse_forecast(weather_info, 1),
            (datetime.date.today() + datetime.timedelta(days=2)).strftime(r'%Y-%m-%d'): self.parse_forecast(weather_info, 2)
        }

        for _time, forec in forecasts.items():
            if not forec: continue
            prefix = color.orange(f'[Weather forecast for {weather_info["city"]["name"]}, {weather_info["city"]["country"]} for {_time}]')
            responses = []

            responses.append(f'{self.colorize_temp(forec.min_temp)} °C to {self.colorize_temp(forec.max_temp)} °C')
            responses.append(f'{forec.conditions}')
            if forec.avg_humidity: responses.append(f'average relative humidity: {forec.avg_humidity}%')
            if forec.avg_wind_speed: responses.append(f'average wind speed: {forec.avg_wind_speed}mps')

            self.bot.say(f'{prefix} {" :: ".join(responses)}')

    @utils.timed_lru_cache(expiration=datetime.timedelta(minutes=3), typed=True)
    def get_weather_info(self, city_name):
        result = self.get_weather_info_impl(city_name)
        if not result:
            # openweathermap behaves strange, sometimes it requires national characters and sometimes not
            city_name = utils.remove_national_chars(city_name)
            self.logger.info(f'getting weather in {city_name}')
            result = self.get_weather_info_impl(city_name)

        return result

    def get_weather_info_impl(self, city_name):
        ask = urllib.parse.quote(city_name)
        raw_response = requests.get(self.weather_url % (ask, self.config['openweathermap_api_key'])).content.decode('utf-8')
        response = json.loads(raw_response)
        if 'cod' not in response or int(response['cod']) != 200:
            if 'cod' not in response or int(response['cod']) != 404:
                self.logger.warning(f'openweathermap error: {raw_response}')
                
            return None

        return response

    @utils.timed_lru_cache(expiration=datetime.timedelta(minutes=3), typed=True)
    def get_forecast_info(self, city_name):
        result = self.get_forecast_info_impl(city_name)
        if not result:
            # openweathermap behaves strange, sometimes it requires national characters and sometimes not
            city_name = utils.remove_national_chars(city_name)
            self.logger.info(f'getting weather forecast in {city_name}')
            result = self.get_forecast_info_impl(city_name)

        return result

    # openweathermap API is really fucked up, I know there's ugly code duplication here...
    def get_forecast_info_impl(self, city_name):
        ask = urllib.parse.quote(city_name)
        raw_response = requests.get(self.forecast_url % (ask, self.config['openweathermap_api_key'])).content.decode('utf-8')
        response = json.loads(raw_response)
        if 'cod' not in response or int(response['cod']) != 200:
            if 'cod' not in response or int(response['cod']) != 404:
                self.logger.warning(f'openweathermap error: {raw_response}')
                
            return None

        return response

    def parse_forecast(self, weather_info, days, night=False):
        dt_txt = (datetime.date.today() + datetime.timedelta(days=days)).strftime(r'%Y-%m-%d')
        if not night:
            wanted_dt_txts = [f'{dt_txt} {x}' for x in ['06:00:00', '09:00:00', '12:00:00', '15:00:00', '18:00:00', '21:00:00']]
        else:
            wanted_dt_txts = [f'{dt_txt} {x}' for x in ['00:00:00', '03:00:00', '06:00:00']]

        min_temp = 99999
        max_temp = -99999
        avg_humidity = 0.
        humidities = 0
        avg_wind_speed = 0.
        wind_speeds = 0
        conditions = []

        for forec in weather_info['list']:
            if forec['dt_txt'] not in wanted_dt_txts or 'main' not in forec: continue
            if forec['main']['temp_min'] < min_temp: min_temp = forec['main']['temp_min']
            if forec['main']['temp_max'] > max_temp: max_temp = forec['main']['temp_max']
            if 'humidity' in forec['main']:
                avg_humidity += forec['main']['humidity']
                humidities += 1

            if 'wind' in forec and 'speed' in forec['wind']:
                avg_wind_speed += forec['wind']['speed']
                wind_speeds += 1

            if 'weather' in forec and len(forec['weather']) > 0:
                cond = forec['weather'][0]
                if cond['id'] == 800: continue  # clear sky
                conditions.append(cond['description'])

        if min_temp == 99999: return None  # no data found
        conditions = list(set(conditions))

        return self.forecast_info(int(max_temp),
                                  int(min_temp),
                                  int(avg_wind_speed / wind_speeds) if wind_speeds != 0 else None,
                                  int(avg_humidity / humidities) if humidities != 0 else None,
                                  ', '.join(conditions if conditions else ['clear sky']))

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
        else:         return color.red(temp)
