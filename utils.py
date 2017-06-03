import sys
import logging

from ruamel.yaml.comments import CommentedMap

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


class c_AssertionError(Exception):
    pass


def c_assert(expr, text):
    if not expr: raise c_AssertionError(text)


def ensure_config_is_ok(config):
    class config_key_info:
        def __init__(self, required, type):
            self.required = required
            self.type = type
            
    config_keys = {
        'server': config_key_info(True, str),
        'port': config_key_info(True, int),
        'channel': config_key_info(True, str),
        'nickname': config_key_info(True, list),
        'use_ssl': config_key_info(True, bool),
        'flood_protection': config_key_info(True, bool),
        'max_autorejoin_attempts': config_key_info(True, int),
        'ops': config_key_info(True, list),
        'colors': config_key_info(True, bool),
        'debug': config_key_info(False, bool),
        'password': config_key_info(False, list),
        'disabled_plugins': config_key_info(False, list),
        'enabled_plugins': config_key_info(False, list),
        'ignored_users': config_key_info(False, list),
        'file_logging_level': config_key_info(True, str),
        'stdout_logging_level': config_key_info(True, str),
        'command_prefix': config_key_info(True, str),
    }

    for key, value in config.items():
        if type(value) is not dict:  # dict is config for plugin
            if type(value) is not CommentedMap:  # CommentedMap is special order-aware dict from ruamel.yaml
                c_assert(key in config_keys, f'unknown config file key: {key}')

    for key, key_info in config_keys.items():
        if key_info.required:
            c_assert(key in config, f'you have to specify {key} field')

        if key in config:
            c_assert(type(config[key]) is key_info.type, f'{key} field type should be {key_info.type.__name__}')

    c_assert(config['server'].strip(), 'you have to specify server address')

    c_assert(config['port'] >= 1024, 'port should be >= 1024')
    c_assert(config['port'] <= 49151, 'port should be <= 49151')
    c_assert(config['channel'].startswith('#'), 'channel should start with #')
    c_assert(config['nickname'], 'you have to specify at least one nickname to use')
    c_assert(config['max_autorejoin_attempts'] >= 0, 'max_autorejoin_attempts should be >= 0')

    if 'disabled_plugins' in config:
        c_assert('enabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified')

    if 'enabled_plugins' in config:
        c_assert('disabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified')

    c_assert(config['file_logging_level'] in logging_level_str_to_int, f'file_logging_level can be one of: {", ".join((logging_level_str_to_int.keys()))}')
    c_assert(config['stdout_logging_level'] in logging_level_str_to_int, f'stdout_logging_level can be one of: {", ".join((logging_level_str_to_int.keys()))}')
    c_assert(config['command_prefix'].strip(), 'you have to specify command prefix')


class yaml_config(dict):
    def __getattr__(self, attr):
        res = super().__getitem__(attr)
        if type(res) is dict: return yaml_config(res)
        if type(res) is yaml_config: return res
        else: return res
