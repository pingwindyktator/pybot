import sys

import logging

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
    c_assert('server' in config, 'you have to specify server address')
    c_assert(type(config['server']) is str, 'server field type should be string')
    c_assert(config['server'], 'you have to specify server address')

    c_assert('port' in config, 'you have to specify port')
    c_assert(type(config['port']) is int, 'port field type should be integer')
    c_assert(config['port'] >= 1024, 'port should be >= 1024')
    c_assert(config['port'] <= 49151, 'port should be <= 49151')

    c_assert('channel' in config, 'you have to specify channel to join')
    c_assert(type(config['channel']) is str, 'channel field type should be string')
    c_assert(config['channel'], 'you have to specify channel to join')
    c_assert(config['channel'].startswith('#'), 'channel should start with #')

    c_assert('nickname' in config, "you have to specify at least one nickname to use")
    c_assert(type(config['nickname']) is list, 'nickname field type should be list')
    c_assert(config['nickname'], 'you have to specify at least one nickname to use')

    c_assert('use_ssl' in config, 'you have to specify whether to use sll or not')
    c_assert(type(config['use_ssl']) is bool, 'use_ssl field type should be boolean')

    c_assert('max_autorejoin_attempts' in config, 'you have to specify maximum number of autorejoin attempts')
    c_assert(type(config['max_autorejoin_attempts']) is int, 'max_autorejoin_attempts field type should be int')
    c_assert(config['max_autorejoin_attempts'] >= 0, 'max_autorejoin_attempts should be >= 0')

    c_assert('ops' in config, 'you have to specify bot operators (can be empty)')
    c_assert(type(config['ops']) is list, 'ops field type should be list')

    if 'debug' in config:
        c_assert(type(config['debug']) is bool, 'debug field type should be boolean')

    if 'password' in config:
        c_assert(type(config['password']) is list, 'password field type should be list')

    if 'disabled_plugins' in config:
        c_assert('enabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified')
        c_assert(type(config['disabled_plugins']) is list, 'disabled_plugins field type should be list')

    if 'enabled_plugins' in config:
        c_assert('disabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified')
        c_assert(type(config['enabled_plugins']) is list, 'enabled_plugins field type should be list')

    if 'banned_users' in config:
        c_assert(type(config['banned_users']) is list, 'banned_users field type should be list')

    c_assert('file_logging_level' in config, 'you have to specify file logging level')
    c_assert(config['file_logging_level'] in logging_level_str_to_int, f'file_logging_level can be one of: {", ".join((logging_level_str_to_int.keys()))}')
    c_assert('stdout_logging_level' in config, 'you have to specify stdout logging level')
    c_assert(config['stdout_logging_level'] in logging_level_str_to_int, f'stdout_logging_level can be one of: {", ".join((logging_level_str_to_int.keys()))}')

    c_assert('command_prefix' in config, 'you have to specify command prefix')
    c_assert(type(config['command_prefix']) is str, 'command_prefix field type should be string')
    c_assert(config['command_prefix'].strip(), 'you have to specify command prefix')
