import requests
from plugin import *


class man(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.man_url = r'http://man.he.net/?topic=%s&section=all'

    @command
    def man(self, sender_nick, args, **kwargs):
        if not args: return
        ask = args[0].strip()
        url = self.man_url % ask
        self.logger.info('%s asked for man of %s' % (sender_nick, ask))

        content = requests.get(url, timeout=5).content
        start = content.find(b'DESCRIPTION\n')
        end = content.find(b'\n\n', start)
        if start == -1 or end == -1:
            self.bot.say('no manual entry for %s' % ask)
            return

        result = content[start + 19:end].replace(b'       ', b'').replace(b'-\n', b'').replace(b'\n', b' ').replace(b'  ', b' ').decode('utf-8').strip()

        if self.bot.is_msg_too_long(result):
            self.bot.msg(sender_nick, result)
        else:
            self.bot.say(color.orange('[%s] ' % ask) + result)

        self.bot.say(color.orange('[%s] ' % ask) + url)
