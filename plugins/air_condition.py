import requests

from datetime import timedelta
from fuzzywuzzy import process, fuzz
from plugin import *


# TODO measurement time?
# TODO performance
# TODO too many stations
# TODO search by street name

class air_condition(plugin):
    class station:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class measurement:
        def __init__(self, what, index_level, value):
            self.what = what
            self.index_level = index_level
            self.value = value

    class condition:
        def __init__(self, station, measurements):
            self.station = station
            self.measurements = measurements

    def __init__(self, bot):
        super().__init__(bot)
        self.stations_by_city = {}  # city_name -> [stations]

    @command
    @command_alias('pollution')
    @doc('air <city>: get air conditions in <city> from gios.gov.pl')
    def air(self, sender_nick, msg, **kwargs):
        if not msg: return

        city_name = self.get_city_name(msg)
        if city_name is None:
            self.bot.say_err()
            return

        self.logger.info(f'{sender_nick} asks for air conditions in {city_name}')
        conditions = [c for c in self.get_air_condition(city_name) if c.measurements]
        if not conditions:
            self.bot.say_err()
            return

        for condition in conditions:
            prefix = color.cyan(f'[{condition.station.name}]')
            measurements = []
            for measurement in condition.measurements:
                if measurement.value > self.get_pollution_standard(measurement.what):
                    standard_percent = f' ({measurement.value / self.get_pollution_standard(measurement.what) * 100.:.0f}%)'
                else:
                    standard_percent = ''

                measurements.append(self.colorize(f'{measurement.what}{standard_percent}', measurement.index_level))

            self.bot.say(f'{prefix} {" :: ".join(measurements)}')

    @utils.timed_lru_cache(expiration=timedelta(minutes=30), typed=True)
    def get_air_condition(self, city_name):
        self.update_known_stations()
        return [self.condition(station, self.get_measurements(station.id)) for station in self.stations_by_city[city_name]]

    @utils.timed_lru_cache(typed=True)
    def get_city_name(self, msg, ignore_national_chars=False):
        self.update_known_stations()
        if ignore_national_chars:
            msg = utils.remove_national_chars(msg)
            stations = {utils.remove_national_chars(city): city for city in self.stations_by_city.keys()}
            result = process.extract(msg, stations.keys(), scorer=fuzz.token_sort_ratio)
            return stations[result[0][0]] if result and len(result[0]) > 1 and result[0][1] > 65 else None
        else:
            result = process.extract(msg, self.stations_by_city.keys(), scorer=fuzz.token_sort_ratio)
            return result[0][0] if result and len(result[0]) > 1 and result[0][1] > 65 else self.get_city_name(msg, ignore_national_chars=True)

    @utils.timed_lru_cache(expiration=timedelta(hours=12))
    def update_known_stations(self):
        response = requests.get(r'http://api.gios.gov.pl/pjp-api/rest/station/findAll', timeout=10).json()
        stations_by_city = {}
        for station in response:
            city = station['city']['name']
            if city not in stations_by_city: stations_by_city[city] = []
            stations_by_city[city].append(self.station(station['id'], station['stationName']))

        self.stations_by_city = stations_by_city
        self.get_city_name.clear_cache()

    def get_measurements(self, station_id):
        result = []
        index_response = requests.get(r'http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/%s' % station_id, timeout=10).json()

        for sensor_id in self.get_station_sensors(station_id):
            data_response = requests.get(r'http://api.gios.gov.pl/pjp-api/rest/data/getData/%s' % sensor_id, timeout=10).json()
            index_level = self.get_index_level(index_response, data_response['key'])
            value = self.get_newest_measurment_value(data_response)
            if value is not None: result.append(self.measurement(data_response['key'], index_level, value))

        return result

    def get_index_level(self, raw_response, sensor_name):
        try:
            sensor_name = sensor_name.casefold().lower().replace('.', '').replace(' ', '')
            return raw_response[f'{sensor_name}IndexLevel']['id']
        except Exception: return -1

    def get_newest_measurment_value(self, raw_response):
        values = raw_response['values']
        values = [v for v in values if 'value' in v and v['value'] is not None]
        if not values: return None
        return sorted(values, key=lambda x: x['date'], reverse=True)[0]['value']

    def get_station_sensors(self, station_id):
        response = requests.get(r'http://api.gios.gov.pl/pjp-api/rest/station/sensors/%s' % station_id, timeout=10).json()
        return [sensor['id'] for sensor in response]

    def colorize(self, str, index_level):
        if index_level < 0: return str
        if index_level == 0: return color.green(str)
        if index_level == 1: return color.light_green(str)
        if index_level == 2: return color.yellow(str)
        if index_level == 3: return color.orange(str)
        if index_level >= 4: return color.light_red(str)

    def get_pollution_standard(self, what):
        what = what.casefold().upper().replace('.', '').replace(' ', '')

        # http://powietrze.gios.gov.pl/pjp/content/annual_assessment_air_acceptable_level
        standards = {
            "PM10": 40,
            "PM25": 25,
            "NO2": 40,
            "SO2": 20,
            "C6H6": 5,
            "CO": 10000,
            "PB": 0.5
        }

        return standards[what] if what in standards else sys.maxsize
