import time

from threading import Thread, Timer, Lock
from irc.client import ServerNotConnectedError


class ping_ponger:
    def __init__(self, connection, interval, on_disconnected_callback):
        self.connection = connection
        self.interval = interval
        self.on_disconnected_callback = on_disconnected_callback
        self.connection.add_global_handler('pong', self._on_pong)
        self.timer = None
        self.thread = None
        self.work = False
        self.mutex = Lock()

    def start(self):
        with self.mutex:
            if self.work: return
            self.work = True
            self.thread = Thread(target=self._ping_pong)
            self.thread.start()

    def stop(self):
        with self.mutex:
            if not self.work: return
            self.work = False
            if self.timer.is_alive(): self.timer.cancel()

    def _on_pong(self, _, raw_msg):
        if raw_msg.source == self.connection.server and self.timer.is_alive(): self.timer.cancel()

    def _on_disconnected(self):
        self.stop()
        self.on_disconnected_callback()

    def _ping_pong(self):
        while self.work:
            time.sleep(self.interval)
            self.timer = Timer(10, self._on_disconnected)
            self.timer.start()
            try: self.connection.ping(self.connection.server)
            except ServerNotConnectedError: pass
            self.timer.join()
