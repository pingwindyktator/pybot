from irc.client import NickMask

from plugin import *


class as_other_user(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.commands_as_other_user_to_send = []

    class as_other_user_command:
        def __init__(self, sender_nick, hacked_nick, connection, raw_msg):
            self.sender_nick = irc_nickname(sender_nick)
            self.hacked_nick = irc_nickname(hacked_nick)
            self.connection = connection
            self.raw_msg = raw_msg

    def on_whoisuser(self, nick, user, host, **kwargs):
        cmds = self.commands_as_other_user_to_send
        try:
            args = next(x for x in cmds if x.hacked_nick == nick)
        except StopIteration: return

        hacked_source = NickMask.from_params(args.hacked_nick, user, host)
        hacked_raw_msg = args.raw_msg
        hacked_raw_msg.source = hacked_source
        hacked_raw_msg.arguments = (hacked_raw_msg.arguments[0],)

        self.logger.warning(f'{args.sender_nick} runs command ({hacked_raw_msg.arguments[0]}) as {args.hacked_nick}')
        self.commands_as_other_user_to_send.remove(args)

        self.bot.on_pubmsg(args.connection, hacked_raw_msg)

    def clean_commands_as_other_user_to_send(self):
        users = self.bot.get_usernames_on_channel()

        for x in self.commands_as_other_user_to_send:
            if x.hacked_nick not in users:
                self.logger.info(f'removing {x.sender_nick} command ({x.raw_msg.arguments[0]}) as {x.hacked_nick}')
                self.commands_as_other_user_to_send.remove(x)

    @command(admin=True)
    @doc('as_other_user <username> <message>: emulate sending <message> as <username>, requires <username> to be online')
    def as_other_user(self, sender_nick, msg, raw_msg, **kwargs):
        if not msg: return
        hacked_nick = irc_nickname(msg.split()[0])
        new_msg = msg[len(hacked_nick):].strip()
        raw_msg.arguments = (new_msg, raw_msg.arguments[1:])
        self.logger.info(f'{sender_nick} queued command ({new_msg}) as {hacked_nick}')
        self.commands_as_other_user_to_send.append(self.as_other_user_command(sender_nick, hacked_nick, self.bot.connection, raw_msg))

        # now we don't know ho to set raw_msg fields (user and host)
        # that's why we are queuing this call, then calling /whois hacked_user
        # when /whois response received, we've got needed user and host so we can do appropriate call
        self.clean_commands_as_other_user_to_send()
        self.bot.whois(hacked_nick)
