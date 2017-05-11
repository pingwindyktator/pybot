import json
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
        self.db_cursor.execute("CREATE TABLE IF NOT EXISTS '%s' (entry TEXT primary key not null, val TEXT)" % self.db_name)  # key -> value
        self.db_mutex = Lock()
        self.case_insensitive_text = 'COLLATE NOCASE' if not self.config['case_sensitive'] else ''

    @command
    def get(self, sender_nick, msg, **kwargs):
        entry = self.prepare_entry(msg)
        with self.db_mutex:
            self.db_cursor.execute("SELECT val FROM '%s' WHERE entry = ? %s" % (self.db_name, self.case_insensitive_text), (entry,))
            result = self.db_cursor.fetchone()

        self.logger.info('%s gets %s: %s' % (sender_nick, entry, result))
        if result: self.bot.say(result[0])

    @command
    @admin
    def rm_set(self, sender_nick, msg, **kwargs):
        entry = self.prepare_entry(msg)
        with self.db_mutex:
            self.db_cursor.execute("DELETE FROM '%s' WHERE entry = ? %s" % (self.db_name, self.case_insensitive_text), (entry,))
            self.db_connection.commit()

        self.logger.info('%s removes %s' % (sender_nick, entry))

    @command
    @admin
    def set(self, sender_nick, msg, **kwargs):
        entry = msg.split()[0]
        val = msg[len(entry):].strip()
        entry = self.prepare_entry(entry)
        try:
            with self.db_mutex:
                self.db_cursor.execute("INSERT INTO '%s' VALUES (?, ?)" % self.db_name, (entry, val))
                self.db_connection.commit()

            self.logger.info('%s sets %s: %s' % (sender_nick, entry, val))
        except sqlite3.IntegrityError as e:
            self.bot.say('"%s" entry already exists' % entry)

    def prepare_entry(self, entry):
        result = entry.strip()
        return result
