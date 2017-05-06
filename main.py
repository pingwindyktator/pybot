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
    assert 'server' in config
    assert type(config['server']) is str
    assert config['server'].strip() != ''

    assert 'port' in config
    assert type(config['port']) is int
    assert config['port'] >= 1024
    assert config['port'] <= 49151

    assert 'channel' in config
    assert type(config['channel']) is str
    assert config['channel'].strip() != ''
    assert config['channel'].startswith('#')

    assert 'nickname' in config
    assert type(config['nickname']) is list
    assert len(config['nickname']) > 0

    assert 'use_ssl' in config
    assert type(config['use_ssl']) is bool

    assert 'max_autorejoin_attempts' in config
    assert type(config['max_autorejoin_attempts']) is int
    assert config['max_autorejoin_attempts'] >= 0

    assert 'ops' in config
    assert type(config['ops']) is list
    assert 'file_logging_level' in config, 'you have to specify file logging level'
    assert config['file_logging_level'] in level_str_to_int, 'file_logging_level can be one of: %s' % ', '.join((level_str_to_int.keys()))
    assert 'stdout_logging_level' in config, 'you have to specify stdout logging level'
    assert config['stdout_logging_level'] in level_str_to_int, 'stdout_logging_level can be one of: %s' % ', '.join((level_str_to_int.keys()))


def main():
    config = yaml.load(open("pybot.yaml"))
    ensure_config_file_is_ok(config)
    configure_logger(config)
    bot = pybot(config)
    bot.start()


if __name__ == "__main__":
    main()
