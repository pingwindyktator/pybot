import logging
import sys
import utils

from ruamel import yaml
from plugins import *
from pybot import pybot


def configure_logger(config):
    logging_format = '%(levelname)-10s%(asctime)s %(filename)s:%(funcName)-16s: %(message)s'
    log_formatter = logging.Formatter(logging_format)
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('pybot.log')
    file_handler.setFormatter(log_formatter)
    level = utils.logging_level_str_to_int[config['file_logging_level']]
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_formatter)
    level = utils.logging_level_str_to_int[config['stdout_logging_level']]
    stdout_handler.setLevel(level)
    root_logger.addHandler(stdout_handler)


def main():
    try:
        config = yaml.load(open("pybot.yaml"), Loader=yaml.Loader)
    except Exception as e:
        print(f'Cannot read config file: {e}')
        sys.exit(6)

    try:
        utils.ensure_config_is_ok(config, assert_unknown_keys=True)
    except utils.config_error as e:
        print(f'Invalid config file: {e}')
        sys.exit(3)

    configure_logger(config)
    bot = pybot(config)
    bot.start()


if __name__ == "__main__":
    main()
