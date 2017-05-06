import logging
import sys
import yaml

from plugins import *
from pybot import pybot

level_str_to_int = {
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


def configure_logger(config):
    logging_format = '%(levelname)-10s%(asctime)s %(filename)s:%(funcName)-16s: %(message)s'
    log_formatter = logging.Formatter(logging_format)
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('pybot.log')
    file_handler.setFormatter(log_formatter)
    level = level_str_to_int[config['file_logging_level']]
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_formatter)
    level = level_str_to_int[config['stdout_logging_level']]
    stdout_handler.setLevel(level)
    root_logger.addHandler(stdout_handler)


def ensure_config_file_is_ok(config):
    try:
        assert 'server' in config, 'you have to specify server address'
        assert type(config['server']) is str, 'server field type should be string'
        assert config['server'], 'you have to specify server address'

        assert 'port' in config, 'you have to specify port'
        assert type(config['port']) is int, 'port field type should be integer'
        assert config['port'] >= 1024, 'port should be >= 1024'
        assert config['port'] <= 49151, 'port should be <= 49151'

        assert 'channel' in config, 'you have to specify channel to join'
        assert type(config['channel']) is str, 'channel field type should be string'
        assert config['channel'], 'you have to specify channel to join'
        assert config['channel'].startswith('#'), 'channel should start with #'

        assert 'nickname' in config, "you have to specify at least one nickname to use"
        assert type(config['nickname']) is list, 'nickname field type should be list'
        assert config['nickname'], 'you have to specify at least one nickname to use'

        assert 'use_ssl' in config, 'you have to specify whether to use sll or not'
        assert type(config['use_ssl']) is bool, 'use_ssl field type should be boolean'

        assert 'max_autorejoin_attempts' in config, 'you have to specify maximum number of autorejoin attempts'
        assert type(config['max_autorejoin_attempts']) is int, 'max_autorejoin_attempts field type should be int'
        assert config['max_autorejoin_attempts'] >= 0, 'max_autorejoin_attempts should be >= 0'

        assert 'ops' in config, 'you have to specify bot operators (can be empty)'
        assert type(config['ops']) is list, 'ops field type should be list'

        if 'debug' in config:
            assert type(config['debug']) is bool, 'debug field type should be boolean'

        if 'password' in config:
            assert type(config['password']) is list, 'password field type should be list'

        if 'disabled_plugins' in config:
            assert 'enabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified'
            assert type(config['disabled_plugins']) is list, 'disabled_plugins field type should be list'

        if 'enabled_plugins' in config:
            assert 'disabled_plugins' not in config, 'you cannot have both enabled_plugins and disabled_plugins specified'
            assert type(config['enabled_plugins']) is list, 'enabled_plugins field type should be list'

        if 'banned_users' in config:
            assert type(config['banned_users']) is list, 'banned_users field type should be list'

        assert 'file_logging_level' in config, 'you have to specify file logging level'
        assert config['file_logging_level'] in level_str_to_int, 'file_logging_level can be one of: %s' % ', '.join((level_str_to_int.keys()))
        assert 'stdout_logging_level' in config, 'you have to specify stdout logging level'
        assert config['stdout_logging_level'] in level_str_to_int, 'stdout_logging_level can be one of: %s' % ', '.join((level_str_to_int.keys()))

        assert 'command_prefix' in config, 'you have to specify command prefix'
        assert type(config['command_prefix']) is str, 'command_prefix field type should be string'
        assert config['command_prefix'].strip(), 'you have to specify command prefix'
    except AssertionError as e:
        print(e)
        sys.exit(3)


def main():
    config = yaml.load(open("pybot.yaml"))
    ensure_config_file_is_ok(config)
    configure_logger(config)
    bot = pybot(config)
    bot.start()


if __name__ == "__main__":
    main()
