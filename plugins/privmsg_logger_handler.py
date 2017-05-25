import copy

from plugin import *


class irc_privmsg_logger_handler(logging.StreamHandler):
    def __init__(self, connection, plhs):
        super().__init__()
        self.plhs = plhs
        self.connection = connection

    def emit(self, record):
        if record.funcName == 'send_raw': return
        try:
            msg = self.format(record)
            for target, level in self.plhs.items():
                if record.levelno >= level and self.connection.is_connected():
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
        self.plh_handler = irc_privmsg_logger_handler(self.bot.connection, self.plhs)
        self.plh_handler.setFormatter(logging.Formatter('%(levelname)-10s%(filename)s:%(funcName)-16s: %(message)s'))
        self.plh_handler.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(self.plh_handler)

    def unload_plugin(self):
        logging.getLogger('').removeHandler(self.plh_handler)

    @command
    @admin
    @doc('add_plh <level>: add privmsg logger handler at <level> level. bot will send you app logs in a private message')
    def add_plh(self, sender_nick, args, **kwargs):
        if not args: return
        level = args[0].strip().lower()
        if level not in utils.logging_level_str_to_int: return
        self.logger.warning(f'plh added: {sender_nick} at {level}')
        level = utils.logging_level_str_to_int[level]
        self.plhs[sender_nick] = level
        self.bot.say(f'plh added: {sender_nick} at {utils.int_to_logging_level_str[level]}')

    @command
    @admin
    @doc('remove saved privmsg logger handler')
    def rm_plh(self, sender_nick, **kwargs):
        if sender_nick not in self.plhs: return
        del self.plhs[sender_nick]
        self.logger.info(f'plh for {sender_nick} removed')
        self.bot.say('plh removed')

    @command
    @doc('get all registered privmsg logger handlers')
    def get_plhs(self, sender_nick, **kwargs):
        response = copy.deepcopy(self.plhs)
        for target, level in response.items():
            response[target] = utils.int_to_logging_level_str[level]

        self.bot.say(f'privmsg logger handlers registered: {response}')
        self.logger.info(f'plhs given to {sender_nick}: {response}')
