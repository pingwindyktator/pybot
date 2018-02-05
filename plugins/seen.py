import json
import os
import sqlite3

from datetime import datetime
from threading import Lock
from plugin import *


class seen(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = self.bot.config['channel']
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        if self.config['clear_db_at_startup']:
            self.db_cursor.execute(f"DROP TABLE IF EXISTS '{self.db_name}'")
            self.db_connection.commit()
            self.logger.info(f"table '{self.db_name}' dropped")

        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nickname TEXT primary key not null, data TEXT)")  # nickname -> seen_data
        self.db_mutex = Lock()

    class activity_type:
        pubmsg = 0
        join = 1
        part = 2
        nick_changed = 3
        kicked = 4
        quit = 5
        ctcp = 6

    class seen_data:
        def __init__(self, timestamp, activity, data):
            self.timestamp = timestamp
            self.activity = activity
            self.data = data

        def to_json(self):
            return json.dumps(self.__dict__)

        @classmethod
        def from_json(cls, serialized):
            serialized = json.loads(serialized)
            return cls(serialized['timestamp'], serialized['activity'], serialized['data'])

        def to_response(self, nickname):
            now = datetime.now()
            timestamp = datetime.strptime(self.timestamp, r'%d-%m-%Y %H:%M:%S')
            remainder = (now - timestamp).total_seconds()

            days, remainder = divmod(remainder, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            delta_time = []
            if days > 0: delta_time.append(f'{days:.0f} days')
            if hours > 0: delta_time.append(f'{hours:.0f} hours')
            if minutes > 0: delta_time.append(f'{minutes:.0f} minutes')
            if seconds > 0: delta_time.append(f'{seconds:.0f} seconds')
            delta_time = ', '.join(delta_time)

            if self.activity == seen.activity_type.pubmsg:
                return f'{nickname} was last seen {delta_time} ago saying "{self.data[0]}"'
            if self.activity == seen.activity_type.ctcp:
                return f'{nickname} was last seen {delta_time} ago doing "{nickname} {self.data[0]}"'
            if self.activity == seen.activity_type.join:
                return f'{nickname} was last seen {delta_time} ago joining channel'
            if self.activity == seen.activity_type.part:
                return f'{nickname} was last seen {delta_time} ago quitting channel'
            if self.activity == seen.activity_type.nick_changed:
                return f'{nickname} was last seen {delta_time} ago changing nickname to {self.data[0]}'
            if self.activity == seen.activity_type.kicked:
                return f'{nickname} was last seen {delta_time} ago kicked by {self.data[0]}'
            if self.activity == seen.activity_type.quit:
                return f'{nickname} was last seen {delta_time} ago disconnecting from server'
            else:
                raise RuntimeError(f"seen_data: ups, you didn't implemented case for activity_type={self.activity}")

    def on_pubmsg(self, source, msg, **kwargs):
        self.update_database(irc_nickname(source.nick), [msg], self.activity_type.pubmsg)

    def on_ctcp(self, source, msg, **kwargs):
        self.update_database(irc_nickname(source.nick), [msg], self.activity_type.ctcp)

    def on_join(self, source, **kwargs):
        if not self.config['register_pubmsg_only']:
            self.update_database(irc_nickname(source.nick), [], self.activity_type.join)

    def on_part(self, source, **kwargs):
        if not self.config['register_pubmsg_only']:
            self.update_database(irc_nickname(source.nick), [], self.activity_type.part)

    def on_quit(self, source, **kwargs):
        if not self.config['register_pubmsg_only']:
            self.update_database(irc_nickname(source.nick), [], self.activity_type.quit)

    def on_nick(self, old_nickname, new_nickname, **kwargs):
        if not self.config['register_pubmsg_only']:
            self.update_database(irc_nickname(old_nickname), [new_nickname], self.activity_type.nick_changed)

    def on_kick(self, who, source, **kwargs):
        if not self.config['register_pubmsg_only']:
            self.update_database(irc_nickname(who), [source.nick], self.activity_type.kicked)

    def update_database(self, nickname, data, activity):
        nickname = irc_nickname(nickname)
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        serialized = self.seen_data(timestamp, activity, data).to_json()

        with self.db_mutex:
            self.db_cursor.execute(f"INSERT OR REPLACE into '{self.db_name}' VALUES (?, ?)", (nickname, serialized))
            self.db_connection.commit()

        self.logger.debug(f'new database entry: {nickname} -> {serialized}')

    @command
    @doc('seen <nickname>: get last activity of <nickname>')
    def seen(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])
        self.logger.info(f'{sender_nick} asks about {nickname}')

        if nickname == self.bot.get_nickname():
            self.bot.say("I'm here, bro")
            return

        if nickname == sender_nick:
            self.bot.say('o rly?')
            return

        if self.bot.is_user_ignored(nickname):
            self.bot.say(f"{nickname} is ignored, I can't help you with than :(")
            return

        with self.db_mutex:
            self.db_cursor.execute(f"SELECT nickname, data FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (nickname,))
            exact_results = self.db_cursor.fetchall()
            self.db_cursor.execute(f"SELECT nickname, data FROM '{self.db_name}' WHERE nickname LIKE ? COLLATE NOCASE", (f'%{nickname}%',))
            possible_results = self.db_cursor.fetchall()

        exact_result = None
        if exact_results:
            possible_results = list(filter(lambda x: x not in exact_results, possible_results))  # remove all exact_results from possible_results
            exact_result = self.get_best_result(exact_results)
            self.bot.say(self.seen_data.from_json(exact_result[1]).to_response(exact_result[0]))

        if possible_results:
            possible_result = self.get_best_result(possible_results)
            if not exact_result or self.get_strptimed_timestamp(exact_result[1]) < self.get_strptimed_timestamp(possible_result[1]):
                # if there wasn't exact_result or possible_result is better
                self.bot.say(self.seen_data.from_json(possible_result[1]).to_response(possible_result[0]))

        if not exact_results and not possible_results:
            self.bot.say_err(nickname)

    def get_best_result(self, serialized_iterable):
        return max(serialized_iterable, key=lambda x: self.get_strptimed_timestamp(x[1]))

    def get_strptimed_timestamp(self, serialized_data):
        return datetime.strptime(self.seen_data.from_json(serialized_data).timestamp, r'%d-%m-%Y %H:%M:%S')
