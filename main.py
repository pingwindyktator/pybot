import logging
import sys
import yaml

from plugins import *
from pybot import pybot


def configure_logger():
    logging_format = '%(levelname)-10s%(asctime)s %(filename)s:%(funcName)-16s: %(message)s'
    log_formatter = logging.Formatter(logging_format)
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('pybot.log')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)


def main():
    configure_logger()
    config = yaml.load(open("pybot.yaml"))
    bot = pybot(config)
    bot.start()


if __name__ == "__main__":
    main()
