import sys
import logging
import unidecode
import tzlocal

from threading import Timer, RLock
from datetime import datetime, timedelta
from functools import total_ordering, wraps, update_wrapper

logging_level_str_to_int = {
    'disabled': sys.maxsize,
    'critical': logging.CRITICAL,
    'fatal': logging.FATAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'warn': logging.WARN,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'notset': logging.NOTSET,
    'all': logging.NOTSET
}

int_to_logging_level_str = {
    sys.maxsize: 'disabled',
    logging.CRITICAL: 'critical',
    logging.FATAL: 'fatal',
    logging.ERROR: 'error',
    logging.WARNING: 'warning',
    logging.WARN: 'warn',
    logging.INFO: 'info',
    logging.DEBUG: 'debug',
    logging.NOTSET: 'all',
}


class null_object:
    def __init__(self, *args, **kwargs): pass

    def __call__(self, *args, **kwargs): return self

    def __repr__(self): return "null_object"

    def __nonzero__(self): return 0

    def __getattr__(self, name): return self

    def __setattr__(self, name, value): return self

    def __delattr__(self, name): return self


class timed_lru_cache:
    # TODO do_not_cache
    """
    decorator that caches a function's return value each time it is called
    cache is automatically invalidated after given expiration time
    """
    def __init__(self, expiration=timedelta.max, typed=True):
        """
        :param expiration: timedelta object
        :param typed: treat function calls with different arguments as distinct
        """
        self.expiration = expiration
        self.typed = typed
        self.cache = {}
        self.cache_lock = RLock()
        self.logger = logging.getLogger(__name__)
        self.function = None

    def __call__(self, function):
        def timed_lru_cache_impl(*args, **kwargs):
            call_args = self._concat_args(*args, **kwargs)
            call_repr = self._get_call_repr(*args, **kwargs)
            now = datetime.now()

            try:
                hash(call_args)
            except TypeError:
                self.logger.warning(f'not hashable: {call_repr}')
                return function(*args, **kwargs)

            with self.cache_lock:
                if call_args in self.cache and (now - self.cache[call_args][1] > self.expiration):
                    self.logger.debug(f'cache expired: {call_repr}')
                    del self.cache[call_args]

                if call_args not in self.cache:
                    try:
                        self.cache[call_args] = (function(*args, **kwargs), now)
                        self.logger.debug(f'cached function result: {call_repr} -> {self.cache[call_args][0]}')
                    except Exception:
                        self.logger.warning(f'exception caught calling: {call_repr}, no result cached')
                        raise
                else:
                    self.logger.debug(f'returned cached result: {call_repr} -> {self.cache[call_args][0]}')

                return self.cache[call_args][0]

        self.function = function
        function.clear_cache = self._clear_cache
        return update_wrapper(timed_lru_cache_impl, function)

    def _concat_args(self, *args, **kwargs):
        if self.typed:
            result = args
            if kwargs: result += (self.__magic_separator,) + tuple(sorted(kwargs.items()))
            return result

        return None

    def _get_call_repr(self, *args, **kwargs):
        return f'{self.function.__qualname__}({", ".join([repr(x) for x in args] + [str(k) + "=" + repr(v) for k, v in kwargs.items()])})'

    class __magic_separator: pass

    def _clear_cache(self):
        with self.cache_lock:
            self.cache = {}

        self.logger.debug(f'cache cleared: {self.function.__qualname__}')


class repeated_timer(Timer):
    """
    exception safe, repeating timer
    """

    def run(self):
        while not self.finished.is_set():
            try:
                self.function(*self.args, **self.kwargs)
            except Exception as e:
                logging.getLogger(__name__).warning(f'exception caught calling {self.function.__qualname__}: {type(e).__name__}: {e}, continuing...')

            self.finished.wait(self.interval)

        self.finished.set()


@total_ordering
class irc_nickname(str):
    """
    case-insensitive string
    """

    def __eq__(self, other):
        return self.casefold() == other.casefold()

    def __lt__(self, other):
        return self.casefold() < other.casefold()

    def __hash__(self):
        return hash(self.casefold())


class config_error(Exception):
    pass


def remove_national_chars(s):
    return unidecode.unidecode(s)


def get_str_utc_offset():
    result = tzlocal.get_localzone().utcoffset(datetime.now()).total_seconds()
    lt = result < 0
    result = abs(result)
    hours = int(result // 3600)
    mins = int((result - 3600 * hours) // 60)
    result = f'{hours}:{str(mins).zfill(2)}'
    return f'-{result}' if lt else f'+{result}'


def ensure_config_is_ok(config, assert_unknown_keys=False):
    class config_key_info:
        def __init__(self, required, type):
            self.required = required
            self.type = type

    def c_assert_error(expr, text):
        if not expr: raise config_error(text)

    config_keys = {
        'server': config_key_info(True, str),
        'port': config_key_info(True, int),
        'channel': config_key_info(True, str),
        'nickname': config_key_info(True, list),
        'use_ssl': config_key_info(True, bool),
        'flood_protection': config_key_info(True, bool),
        'max_autorejoin_attempts': config_key_info(True, int),
        'colors': config_key_info(True, bool),
        'file_logging_level': config_key_info(True, str),
        'stdout_logging_level': config_key_info(True, str),
        'command_prefix': config_key_info(True, str),
        'try_autocorrect': config_key_info(True, bool),
        'wrap_too_long_msgs': config_key_info(True, bool),
        'health_check': config_key_info(True, bool),
        'health_check_interval_s': config_key_info(True, int),
        'db_location': config_key_info(True, str),
        'superop': config_key_info(True, str),
        'use_fix_tip': config_key_info(True, bool),

        'password': config_key_info(False, list),
        'disabled_plugins': config_key_info(False, list),
        'enabled_plugins': config_key_info(False, list),
    }

    c_assert_error(config, 'config seems to be empty')

    for key, key_info in config_keys.items():
        if key_info.required:
            c_assert_error(key in config, f'you have to specify {key} field')

        if key in config:
            c_assert_error(type(config[key]) is key_info.type, f'{key} field type should be {key_info.type.__name__}')

    c_assert_error(config['server'].strip(), 'you have to specify server field')
    c_assert_error(config['port'] > 0, 'port should be > 0')
    c_assert_error(config['port'] <= 65535, 'port should be <= 65535')
    c_assert_error(config['channel'].startswith('#'), 'channel should start with #')
    c_assert_error(config['nickname'], 'you have to specify at least one nickname to use')
    c_assert_error(config['max_autorejoin_attempts'] >= 0, 'max_autorejoin_attempts should be >= 0')
    c_assert_error(config['file_logging_level'] in logging_level_str_to_int, f'file_logging_level can be one of: {", ".join((logging_level_str_to_int.keys()))}')
    c_assert_error(config['stdout_logging_level'] in logging_level_str_to_int, f'stdout_logging_level can be one of: {", ".join((logging_level_str_to_int.keys()))}')
    c_assert_error(config['command_prefix'].strip(), 'you have to specify command_prefix field')
    c_assert_error(config['superop'].strip(), 'you have to specify superop field')
    c_assert_error(config['health_check_interval_s'] >= 15, 'health_check_interval_s should be >= 15')

    if 'disabled_plugins' in config:
        c_assert_error('enabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified')

    if 'enabled_plugins' in config:
        c_assert_error('disabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified')

    for nickname in config['nickname']:
        c_assert_error(nickname.strip(), 'you cannot have empty nickname')

    if assert_unknown_keys:
        for key, value in config.items():
            if not isinstance(value, dict): c_assert_error(key in config_keys, f'unknown config file key: {key}')
