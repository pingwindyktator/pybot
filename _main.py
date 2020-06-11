import logging
import shutil
import sys
import os
import utils

from ruamel import yaml
# noinspection PyUnresolvedReferences
from plugins import *
from pybot import pybot


def configure_logger(config):
    logging_format = '%(levelname)-10s%(asctime)s %(name)s:%(funcName)-16s: %(message)s'
    log_formatter = logging.Formatter(logging_format)
    root_logger = logging.getLogger()
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
    if config['filter_stdout_non_pybot_debug_logs']: stdout_handler.addFilter(utils.only_pybot_logs_filter())
    root_logger.addHandler(stdout_handler)


def init_config():
    try:
        if not os.path.exists(utils.CONFIG_FILENAME):
            shutil.copyfile(utils.CONFIG_TEMPLATE_FILENAME, utils.CONFIG_FILENAME)
            print('pybot.yaml config file not found. Its template was created but you probably want to edit it before next run.')
            sys.exit(0)
    except Exception as e:
        print(f'Cannot create config file: {type(e).__name__}: {e}')
        sys.exit(1)

    try:
        config = yaml.load(open(utils.CONFIG_FILENAME), Loader=yaml.Loader)
    except Exception as e:
        print(f'Cannot read config file: {type(e).__name__}: {e}')
        sys.exit(6)

    config_violations = utils.get_config_violations(config, assert_unknown_keys=True)
    if config_violations:
        config_violations_str = '\n'.join(config_violations)
        print(f'Invalid config file:\n{config_violations_str}')
        sys.exit(3)

    return config


def set_timezone(config):
    try:
        utils.set_timezone(config['timezone'])
    except Exception as e:
        print(f'Cannot set timezone: {type(e).__name__}: {e}')
        sys.exit(10)


def main(debug_mode=True):
    config = init_config()

    if 'debug_mode' in config:
        debug_mode = config['debug_mode']

    if not debug_mode:
        set_timezone(config)
        utils.setup_sentry()
        utils.report_error = utils.report_error_sentry

    configure_logger(config)
    bot = pybot(config, debug_mode)

    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die('Interrupted by owner')
        sys.exit(0)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main(debug_mode=True)
