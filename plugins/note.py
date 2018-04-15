import json
import os
import sqlite3
import string

from datetime import datetime
from threading import Lock
from plugin import *


class note(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = self.bot.get_channel_name()
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nickname TEXT primary key not null, notes TEXT)")  # nickname -> [msgs, to, send]
        self.db_mutex = Lock()

    def on_pubmsg(self, source, **kwargs):
        self.give_notes(source.nick)

    def on_ctcp(self, source, **kwargs):
        self.give_notes(source.nick)

    def on_mode(self, source, **kwargs):
        self.give_notes(source.nick)

    def on_kick(self, source, **kwargs):
        self.give_notes(source.nick)

    def give_notes(self, nickname):
        nickname = irc_nickname(nickname)

        notes = self.get_notes_for_user(nickname, remove=True, exact=not self.config['search_for_possible_notes'])
        if not notes: return

        self.bot.say(f'{nickname}, you have notes!')
        for _note in notes: self.bot.say(_note)

        self.logger.info(f'notes given to {nickname}')

    @command
    @doc('note <nickname> <message>: store <message> for <nickname>')
    def note(self, sender_nick, msg, **kwargs):
        self.note_impl(sender_nick, msg, anon=False)

    @command
    @doc('anote <nickname> <message>: store anonymous <message> for <nickname>')
    def anote(self, sender_nick, msg, **kwargs):
        self.note_impl(sender_nick, msg, anon=True)

    def note_impl(self, sender_nick, msg, anon):
        if not msg: return
        target = msg.split()[0]
        if sender_nick == target or target == self.bot.get_nickname():
            self.bot.say('orly?')
            return

        new_note = msg[len(target):].strip()
        if not new_note: return
        self.logger.info(f'{sender_nick} notes "{new_note}" for {target}')
        new_note = self.build_msg(None if anon else sender_nick, new_note)
        self.save_note(target, new_note)
        self.bot.say_ok()

    def get_notes_for_user(self, nickname, remove=False, exact=False):
        with self.db_mutex:
            if not exact:
                self.db_cursor.execute(f"SELECT nickname, notes FROM '{self.db_name}' WHERE nickname LIKE ? COLLATE NOCASE", (f'%{nickname}%',))
                result = self.db_cursor.fetchall()
                result = [x for x in result if self.is_same_nickname(nickname, x[0])]
            else:
                self.db_cursor.execute(f"SELECT nickname, notes FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (nickname,))
                result = self.db_cursor.fetchone()
                result = [result] if result else None

        if result:
            if remove:
                nicknames = [result[i][0] for i in range(0, len(result))]
                in_str = ', '.join('?' * len(nicknames))
                with self.db_mutex:
                    self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE nickname IN (%s) COLLATE NOCASE" % in_str, (*nicknames,))
                    self.db_connection.commit()

            return sum([json.loads(result[i][1]) for i in range(0, len(result))], [])

        return None

    def build_msg(self, nickname, msg):
        time = datetime.now().strftime("%Y-%m-%d %H:%M")

        if nickname: return f'{time}  <{nickname}> {msg}'
        return f'{time}  {msg}'

    def is_same_nickname(self, a, b):
        strip_str = ' _' + string.digits
        a = a.casefold().strip(strip_str)
        b = b.casefold().strip(strip_str)
        return a == b and a

    def save_note(self, target, new_note):
        saved_notes = self.get_notes_for_user(target, exact=True, remove=False)

        if saved_notes:
            saved_notes.extend([new_note])
            with self.db_mutex:
                self.db_cursor.execute(f"UPDATE '{self.db_name}' SET notes = ? WHERE nickname = ?", (json.dumps(saved_notes), target.casefold()))
                self.db_connection.commit()
        else:
            with self.db_mutex:
                self.db_cursor.execute(f"INSERT INTO '{self.db_name}' VALUES (?, ?)", (target.casefold(), json.dumps([new_note])))
                self.db_connection.commit()
