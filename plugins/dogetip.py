import json
import os
import sqlite3
import urllib.parse
import requests
import block_io
import bcrypt
import re

from threading import Lock
from plugin import *

# TODO doge_withdraw

class dogetip(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.blockio = block_io.BlockIo(self.config['block_io_api_key'], self.config['block_io_api_pin'])
        self.db_name = self.bot.get_server_name()
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nick TEXT primary key not null, pin TEXT not null, salt TEXT, trusted_hostnames TEXT)")  # nick -> {pin, salt, trusted_hostnames}
        self.db_mutex = Lock()
        self.auth_required = {}  # sender_nick -> {funcs_to_run_after_auth}
        self.password_awaiting_str = 'NOTSET_97bfc2390a276969b10c6'

        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE pin = ?", (self.password_awaiting_str,))
            self.db_connection.commit()

    def gen_id_for_nick(self, nick):
        return f'{nick.casefold()}@{self.bot.get_server_name()}'

    def get_qr_code(self, addr):
        msg = urllib.parse.quote(addr)
        link = r'http://chart.googleapis.com/chart?cht=qr&chs=400x400&chl=%s' % msg

        raw_response = requests.get(r'https://is.gd/create.php?format=simple&url=%s' % urllib.parse.quote(link))
        if raw_response.status_code == requests.codes.ok and raw_response.content:
            return raw_response.content.decode()

        return link

    def is_registered(self, nick):
        result = self.get_user_pin(nick)
        return result is not None and result != self.password_awaiting_str

    def is_valid_addr(self, addr):
        return self.blockio.is_valid_address(addr)['data']['is_valid']

    def auth_and_execute(self, source, func, not_trusted_msg=''):
        sender_nick = irc_nickname(source.nick)
        if self.is_registered(sender_nick) and self.is_hostname_trusted(source):
            self.logger.info(f'{sender_nick} is authenticated on {source.host}, executing command...')
            func()
        else:
            self.logger.info(f'{sender_nick} is NOT authenticated on {source.host}, awaiting pin...')
            self.bot.say(not_trusted_msg)
            self.auth_required.setdefault(sender_nick, []).append(func)

    def execute_all_auth_required_funcs(self, sender_nick):
        funcs_to_run = self.auth_required.setdefault(sender_nick, []).copy()
        for func in funcs_to_run: func()
        self.auth_required[sender_nick] = []

    def get_user_pin(self, nick):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT pin FROM '{self.db_name}' WHERE nick = ?", (nick.casefold(),))
            result = self.db_cursor.fetchone()

        return result[0] if result else None

    def is_password_correct(self, nick, password):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT pin, salt FROM '{self.db_name}' WHERE nick = ?", (nick.casefold(),))
            pin, salt = self.db_cursor.fetchone()

        return bcrypt.hashpw(password.encode(), salt) == pin

    def set_password(self, nick, pin):
        salt = bcrypt.gensalt()
        hashed_pin = bcrypt.hashpw(pin.encode(), salt)

        with self.db_mutex:
            self.db_cursor.execute(f"UPDATE '{self.db_name}' SET pin = ?, salt = ? WHERE nick = ?", (hashed_pin, salt, nick.casefold()))
            self.db_connection.commit()

    def get_trusted_hostnames(self, nick):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT trusted_hostnames FROM '{self.db_name}' WHERE nick = ?", (nick.casefold(),))
            result = self.db_cursor.fetchone()

        return json.loads(result[0]) if result and result[0] else []

    def is_hostname_trusted(self, source):
        return source.host in self.get_trusted_hostnames(irc_nickname(source.nick))

    def trust_hostname(self, nick, hostname):
        hostnames = self.get_trusted_hostnames(nick)
        hostnames.append(hostname)
        self.set_trusted_hostnames(nick, hostnames)

    def set_trusted_hostnames(self, nick, hostnames):
        self.db_cursor.execute(f"UPDATE '{self.db_name}' SET trusted_hostnames = ? WHERE nick = ?", (json.dumps(hostnames), nick.casefold()))
        self.db_connection.commit()

    @utils.repeat_until(no_exception=True)
    def get_address_impl(self, nick):
        label = self.gen_id_for_nick(nick)
        try:
            return self.blockio.get_address_by_label(label=label)['data']['address']
        except Exception:
            return self.blockio.get_new_address(label=label)['data']['address']

    def get_address(self, nick):
        try:
            return self.get_address_impl(nick)
        except Exception as e:
            self.logger.warning(f'cannot generate address for {nick}: {e}')
            raise RuntimeError(f'cannot generate address: {e}')

    def on_privmsg(self, raw_msg, msg, source, **kwargs):
        sender_nick = irc_nickname(source.nick)
        if not len(self.auth_required.setdefault(sender_nick, [])): return

        if self.get_user_pin(sender_nick) == self.password_awaiting_str and self.is_hostname_trusted(source):
            self.logger.info(f'setting the password for {sender_nick}')
            self.set_password(sender_nick, msg.strip())
            self.execute_all_auth_required_funcs(sender_nick)
            return

        if self.is_password_correct(sender_nick, msg.strip()):
            self.logger.info(f'{sender_nick} authenticated')
            self.trust_hostname(sender_nick, source.host)
            self.execute_all_auth_required_funcs(sender_nick)
        else:
            self.bot.say('Incorrect password', sender_nick)

    def register_impl(self, source):
        sender_nick = irc_nickname(source.nick)
        label = self.gen_id_for_nick(sender_nick)
        self.logger.info(f'{sender_nick} registered from {source.host} with label {label}')

        address = self.get_address(sender_nick)
        qrcode = self.get_qr_code(address)
        self.bot.say(f'{sender_nick}: registration completed, your DOGEOCIN address is {address} -> {qrcode}')

    def tip_impl(self, sender_nick, receiver, amount):
        receiver_label = self.gen_id_for_nick(receiver)
        sender_label = self.gen_id_for_nick(sender_nick)

        try:
            self.get_address(receiver)
            txid = self.blockio.withdraw_from_labels(from_labels=sender_label,
                                                     to_labels=receiver_label,
                                                     amounts=amount)['data']['txid']

            self.logger.info(f'sent the tx from {sender_nick}: {txid}')
            self.bot.say(f'{sender_nick} just tipped {receiver} with {amount}Ð [{txid}]')
        except Exception as e:
            self.logger.warning(f'cannot send transaction from {sender_nick}: {e}')
            self.bot.say(f'cannot send transaction: {e}')

    @command
    @doc('register an account to use this plugin, you will need to provide a PIN on privmsg after that')
    def doge_register(self, sender_nick, raw_msg, **kwargs):
        if self.is_registered(sender_nick):
            self.bot.say(f'{sender_nick}: you are already registered')
            return

        with self.db_mutex:
            self.db_cursor.execute(f"INSERT OR REPLACE INTO '{self.db_name}' VALUES (?, ?, ?, ?)", (sender_nick.casefold(), self.password_awaiting_str, '', json.dumps([raw_msg.source.host])))
            self.db_connection.commit()

        self.auth_and_execute(raw_msg.source,
                              lambda: self.register_impl(raw_msg.source),
                              f'{sender_nick}: you need to set-up your PIN, please provide one on privmsg')

    @command
    @doc('get your DOGECOIN address')
    def doge_addr(self, sender_nick, **kwargs):
        if not self.is_registered(sender_nick):
            self.bot.say(f'{sender_nick}: type {self.bot.get_command_prefix()}doge_register to register your account')
            return

        address = self.get_address(sender_nick)
        qrcode = self.get_qr_code(address)

        self.bot.say(f'{sender_nick}: your DOGEOCIN address is {address} -> {qrcode}')

    @command
    @doc('get your DOGECOIN balance')
    def doge_balance(self, sender_nick, **kwargs):
        if not self.is_registered(sender_nick):
            self.bot.say(f'{sender_nick}: type {self.bot.get_command_prefix()}doge_register to register your account')
            return

        label = self.gen_id_for_nick(sender_nick)
        result = self.blockio.get_address_balance(labels=label)['data']
        available, pending = result['available_balance'], result['pending_received_balance']
        self.bot.say(f'{sender_nick}: available balance is {available}Ð, pending balance is {pending}Ð')

    @command
    @doc('forget all trusted hostnames, including current one')
    def doge_forget_hostnames(self, raw_msg, **kwargs):
        sender_nick = irc_nickname(raw_msg.source.nick)

        self.auth_and_execute(raw_msg.source,
                              lambda: self.set_trusted_hostnames(sender_nick, []),
                              f'{sender_nick}: this hostname is not trusted, please authenticate with your PIN on privmsg')

    @command
    @command_alias('tip')
    @doc('doge_tip <nickname> <amount>: tip <nickname> with <amount>Ð, both you and <nickname> have to be registered; tx fee is 1Ð')
    def doge_tip(self, sender_nick, args, raw_msg, **kwargs):
        if not args: return
        receiver = irc_nickname(args[0])
        try: amount = int(args[1])
        except Exception:
            self.bot.say('amount should be an integer')
            return

        if receiver == sender_nick:
            self.bot.say('orly?')
            return

        if receiver == self.bot.get_nickname():
            self.bot.say(':)')
            return

        if not self.is_registered(sender_nick):
            self.bot.say(f'{sender_nick}: type {self.bot.get_command_prefix()}doge_register to register your account')
            return

        if not self.is_registered(receiver):
            self.bot.say(f'{receiver} is not registered')
            if receiver in self.bot.get_usernames_on_channel():
                self.bot.say(f'{receiver}, type {self.bot.get_command_prefix()}doge_register to register your account')

            return

        self.auth_and_execute(raw_msg.source,
                              lambda: self.tip_impl(sender_nick, receiver, amount),
                              f'{sender_nick}: this hostname is not trusted, please authenticate with your PIN on privmsg')
