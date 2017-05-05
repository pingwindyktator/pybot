import logging
import sys
import argparse

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
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser(description='pybot - irc bot')

    parser.add_argument('server', action='store', type=str, help='server:port to connect to')
    parser.add_argument('channel', action='store', type=str, help='channel to join to')
    parser.add_argument('nickname', action='store', type=str, help='nickname:password to use')
    parser.add_argument('-s', '--use-ssl', action='store_true', default=False, help='connect over SSL')
    args = parser.parse_args()
    server = args.server.split(':')[0]
    try:
        port = int(args.server.split(':')[1]) if len(args.server.split(':')) > 1 else 6667
    except ValueError:
        print('error: erroneous port')
        logger.critical('erroneous port given')
        sys.exit(1)
    channel = args.channel if args.channel.startswith('#') else '#' + args.channel
    nickname = args.nickname.split(':')[0]
    password = args.nickname.split(':')[1] if len(args.nickname.split(':')) > 1 else None
    use_ssl = args.use_ssl

    logger.debug('channel: %s' % server)
    logger.debug('port: %d' % port)
    logger.debug('server: %s' % channel)
    logger.debug('nickname: %s' % nickname)
    if password:
        logger.debug('password: %s' % ''.join(['*' for _ in range(0, len(password))]))

    bot = pybot(channel, nickname, server, port, use_ssl, password)
    bot.start()


if __name__ == "__main__":
    main()
