import logging
import threading

log = logging.getLogger(__name__)


class Poller(threading.Thread):
    """Calls fetch() every `interval` seconds and hands the result to deliver().

    After a failure it retries after `retry_interval` instead of waiting a full
    interval, so a slow-starting API is picked up within seconds.
    """

    def __init__(self, fetch, deliver, interval, retry_interval=None):
        super().__init__(daemon=True, name="poller")
        self._fetch, self._deliver = fetch, deliver
        self._interval = interval
        self._retry = min(retry_interval, interval) if retry_interval else interval
        self._stop_event = threading.Event()

    def run(self):
        failures = 0
        while not self._stop_event.is_set():
            wait = self._interval
            try:
                self._deliver(self._fetch())
                if failures:
                    log.info("data source is back after %d failed attempt(s)", failures)
                failures = 0
            except Exception as exc:
                failures += 1
                if failures == 1:
                    log.warning("data fetch failed (%s); retrying every %ss", exc, self._retry)
                elif failures % 10 == 0:
                    log.warning("data fetch still failing after %d attempts: %s", failures, exc)
                wait = self._retry
            self._stop_event.wait(wait)

    def stop(self):
        self._stop_event.set()
