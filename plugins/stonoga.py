import random
from plugin import *


class stonoga(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.replies = ['{}: to jest dramat kurwa', '{}: jeszcze sie zobaczymy i zobaczymy', '{}: wypierdalaj za brame chamie',
                        'was powinno sie jebac', 'szkoda gadac ;/', 'jebany kaczynski smiec']
        self.chance_to_insult = 0.1  # in range [0, 1]

    def on_pubmsg(self, connection, raw_msg):
        if random.uniform(0, 1) > self.chance_to_insult or len(self.replies) == 0: return

        sender_nick = raw_msg.source.nick
        reply = self.get_random_reply().format(sender_nick)
        self.bot.send_response_to_channel(reply)

    def get_random_reply(self):
        pos = random.randint(0, len(self.replies) - 1)
        return self.replies[pos]
