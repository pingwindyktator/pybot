import logging
from plugins import *
import sys
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

    if len(sys.argv) != 4:
        logger.critical('not enough args given (%s)' % (len(sys.argv) - 1))
        print("Usage: pybot <server[:port]> <channel> <nickname[:password]>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            logger.critical('erroneous port given')
            sys.exit(1)
    else:
        port = 6667

    channel = sys.argv[2] if sys.argv[2].startswith('#') else '#' + sys.argv[2]

    n = sys.argv[3].split(':')
    nickname = n[0]
    password = n[1] if len(n) > 1 else ''

    logger.debug('channel: %s' % server)
    logger.debug('port: %d' % port)
    logger.debug('server: %s' % channel)
    logger.debug('nickname: %s' % nickname)
    logger.debug('password: %s' % ''.join(['*' for _ in range(0, len(password))]))

    bot = pybot(channel, nickname, server, port, password)
    bot.start()


if __name__ == "__main__":
    main()
