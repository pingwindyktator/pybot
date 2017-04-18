from plugin import *


class irc_privmsg_logger_handler(logging.StreamHandler):
    def __init__(self, connection, plhs):
        self.plhs = plhs
        self.connection = connection
        super().__init__()

    def emit(self, record):
        try:
            msg = self.format(record)
            for target, level in self.plhs.items():
                if record.levelno >= level:
                    self.connection.privmsg(target, msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class privmsg_logger_handler(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.plhs = {}  # username -> logging_level

    def on_welcome(self, connection, raw_msg):
        root_logger = logging.getLogger('')
        irc_handler = irc_privmsg_logger_handler(connection, self.plhs)
        irc_handler.setFormatter(logging.Formatter('%(levelname)-10s%(filename)s:%(funcName)-16s: %(message)s'))
        root_logger.addHandler(irc_handler)

    @command
    @admin
    def add_plh(self, sender_nick, args, **kwargs):
        level_str_to_int = {
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

        if not args: return
        level = args[0]
        if level not in level_str_to_int: return
        self.logger.warning('plh added: %s at %s' % (sender_nick, args[0]))
        level = level_str_to_int[level]
        self.plhs[sender_nick] = level
        self.bot.send_response_to_channel('plh added: %s at %s' % (sender_nick, args[0]))

    @command
    @admin
    def rm_plh(self, sender_nick, **kwargs):
        if sender_nick not in self.plhs: return
        del self.plhs[sender_nick]
        self.logger.info('plh for %s removed' % sender_nick)
        self.bot.send_response_to_channel('plh removed')

    @command
    @admin
    def get_plhs(self, sender_nick, **kwargs):
        self.bot.send_response_to_channel('privmsg logger handlers registered: %s' % self.plhs)
        self.logger.info('plhs: %s' % self.plhs)
