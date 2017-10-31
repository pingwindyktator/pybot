import time

from threading import Thread, Timer


class ping_ponger:
    def __init__(self, connection, interval, on_disconnected_callback):
        self.connection = connection
        self.interval = interval
        self.on_disconnected_callback = on_disconnected_callback
        self.connection.add_global_handler('pong', self._on_pong)
        self.timer = None
        self.thread = None
        self.work = False

    def start(self):
        if self.work: return
        self.work = True
        self.thread = Thread(target=self._ping_pong)
        self.thread.start()

    def stop(self):
        self.work = False
        if self.timer.is_alive(): self.timer.cancel()

    def _on_pong(self, _, raw_msg):
        if raw_msg.source == self.connection.server: self.timer.cancel()

    def _on_disconnected(self):
        self.stop()
        self.on_disconnected_callback()

    def _ping_pong(self):
        while self.work:
            self.timer = Timer(10, self._on_disconnected)
            self.timer.start()
            self.connection.ping(self.connection.server)
            time.sleep(15)
