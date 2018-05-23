import wikipedia

from plugin import *


# TODO set language
class wiki(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @doc('wiki <ask>: search wikipedia for <ask>')
    def wiki(self, msg, sender_nick, **kwargs):
        if not msg: return
        self.logger.info(f'{sender_nick} asked wikipedia about {msg}')
        ask = wikipedia.search(msg)
        if not ask:
            self.bot.say_err()
            return

        try:
            ask = ask[0]
            page = wikipedia.page(ask)
            summary = wikipedia.summary(ask, sentences=1)
            summary = summary.replace('( listen); ', '').replace('(; ', '(').replace('(; ', '(').replace('  ', ' ').replace('( ', '(')
            prefix = color.orange(f'[{page.title}]')
            self.bot.say(f'{prefix} {summary} {page.url}')
        except wikipedia.exceptions.PageError:
            self.bot.say_err()
        except wikipedia.exceptions.DisambiguationError:
            pass  # TODO
