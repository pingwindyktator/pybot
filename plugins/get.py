import os
import sqlite3

from threading import Lock
from plugin import *


class get(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = "get"
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (entry TEXT primary key not null, val TEXT)")  # key -> value
        self.db_mutex = Lock()
        self.case_insensitive_text = 'COLLATE NOCASE' if not self.config['case_sensitive'] else ''

    @command
    @doc('get <entry>: get saved message for <entry>')
    def get(self, sender_nick, msg, **kwargs):
        entry = self.prepare_entry(msg)
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT val FROM '{self.db_name}' WHERE entry = ? {self.case_insensitive_text}", (entry,))
            result = self.db_cursor.fetchone()

        result = result[0] if result else None
        self.logger.info(f'{sender_nick} gets {entry}: {result}')
        if result: self.bot.say(result)

    @command
    @doc("get all saved messages")
    def get_list(self, sender_nick, **kwargs):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT entry FROM '{self.db_name}'")
            result = self.db_cursor.fetchall()

        result = [t[0] for t in result]
        response = f'saved entries: {", ".join(result)}' if result else 'no saved entries'
        self.bot.say(response)

    @command
    @admin
    @doc('rm_set <entry>: remove <entry> entry')
    def unset(self, sender_nick, msg, **kwargs):
        entry = self.prepare_entry(msg)
        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE entry = ? {self.case_insensitive_text}", (entry,))
            self.db_connection.commit()

        self.bot.say_ok()
        self.logger.info(f'{sender_nick} removes {entry}')

    @command
    @admin
    @doc('set <entry> <message>: save <message> for <entry>')
    def set(self, sender_nick, msg, **kwargs):
        entry = msg.split()[0]
        val = msg[len(entry):].strip()
        entry = self.prepare_entry(entry)
        try:
            with self.db_mutex:
                self.db_cursor.execute(f"INSERT INTO '{self.db_name}' VALUES (?, ?)", (entry, val))
                self.db_connection.commit()

            self.logger.info(f'{sender_nick} sets {entry}: {val}')
            self.bot.say_ok()
        except sqlite3.IntegrityError:
            self.bot.say(f'"{entry}" entry already exists')

    def prepare_entry(self, entry):
        result = entry.strip()
        return result
