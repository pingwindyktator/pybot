import logging
import shutil
import sys
import utils
import os

from ruamel import yaml
from plugins import *
from pybot import pybot


def configure_logger(config):
    class CustomFilter(logging.Filter):
        def filter(self, record):
            return record.pathname.startswith(os.path.dirname(os.path.abspath(__file__))) or record.levelno > logging.DEBUG

    logging_format = '%(levelname)-10s%(asctime)s %(filename)s:%(funcName)-16s: %(message)s'
    log_formatter = logging.Formatter(logging_format)
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('pybot.log')
    file_handler.setFormatter(log_formatter)
    level = utils.logging_level_str_to_int[config['file_logging_level']]
    file_handler.setLevel(level)
    file_handler.addFilter(CustomFilter())
    root_logger.addHandler(file_handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_formatter)
    level = utils.logging_level_str_to_int[config['stdout_logging_level']]
    stdout_handler.setLevel(level)
    stdout_handler.addFilter(CustomFilter())
    root_logger.addHandler(stdout_handler)


def main(debug_mode=False):
    try:
        if not os.path.exists("pybot.yaml"):
            shutil.copyfile('pybot.template.yaml', 'pybot.yaml')
            print("pybot.yaml config file not found. Its template was created but you probably want to edit it before next run.")
            sys.exit(0)
    except Exception as e:
        print(f'Cannot create config file: {type(e).__name__}: {e}')
        sys.exit(1)

    try:
        config = yaml.load(open("pybot.yaml"), Loader=yaml.Loader)
    except Exception as e:
        print(f'Cannot read config file: {type(e).__name__}: {e}')
        sys.exit(6)

    try:
        utils.ensure_config_is_ok(config, assert_unknown_keys=True)
    except utils.config_error as e:
        print(f'Invalid config file: {type(e).__name__}: {e}')
        sys.exit(3)

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
