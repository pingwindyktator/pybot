import wikipedia

from datetime import timedelta
from plugin import *


class wiki(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        wikipedia.set_lang(self.config['language'])

    @command
    @doc('wiki <ask>: search wikipedia for <ask>')
    def wiki(self, msg, sender_nick, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked wikipedia about {msg}')

        try:
            page, summary = self.get_wiki_data(msg)
            if not page or not summary:
                self.bot.say_err()
                return

            prefix = color.orange(f'[{page.title}]')
            result = f'{prefix} {summary}'
            if not self.bot.is_msg_too_long(result):
                self.bot.say(result)

            self.bot.say(f'{prefix} {page.url}')

        except wikipedia.exceptions.PageError:
            self.bot.say_err()
        except wikipedia.exceptions.DisambiguationError as e:
            self.bot.say(f'{e.title} may refer to {", ".join(e.options)}')

    @utils.timed_lru_cache(expiration=timedelta(minutes=3), typed=True)
    def get_wiki_data(self, msg):
        ask = wikipedia.search(msg)
        if not ask:
            return None, None

        ask = ask[0]
        page = wikipedia.page(ask)
        summary = wikipedia.summary(ask, sentences=1)
        summary = summary.replace('( listen); ', '').replace('(; ', '(').replace('( ', '(').replace('  ', ' ')
        return page, summary
