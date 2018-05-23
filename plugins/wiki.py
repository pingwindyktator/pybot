import wikipedia

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
        ask = wikipedia.search(msg)
        if not ask:
            self.bot.say_err()
            return

        try:
            ask = ask[0]
            page = wikipedia.page(ask)
            summary = wikipedia.summary(ask, sentences=1)
            summary = summary.replace('( listen); ', '').replace('(; ', '(').replace('(; ', '(').replace('( ', '(').replace('  ', ' ')
            prefix = color.orange(f'[{page.title}]')
            result = f'{prefix} {summary} {page.url}'
            if self.bot.is_msg_too_long(result): self.bot.say(f'{prefix} {page.url}')
            else: self.bot.say(result)
            
        except wikipedia.exceptions.PageError:
            self.bot.say_err()
        except wikipedia.exceptions.DisambiguationError as e:
            self.bot.say(f'{e.title} may refer to {", ".join(e.options)}')
