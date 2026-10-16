import logging
import threading

log = logging.getLogger(__name__)


class Poller(threading.Thread):
    """Calls fetch() every `interval` seconds and hands the result to deliver()."""

    def __init__(self, fetch, deliver, interval):
        super().__init__(daemon=True, name="poller")
        self._fetch, self._deliver, self._interval = fetch, deliver, interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                self._deliver(self._fetch())
            except Exception:
                log.exception("data fetch failed; keeping the last snapshot")
            self._stop_event.wait(self._interval)

    def stop(self):
        self._stop_event.set()
