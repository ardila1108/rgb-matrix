import logging
import threading
import time

log = logging.getLogger(__name__)


class Poller(threading.Thread):
    """Calls fetch() every `interval` seconds and hands the result to deliver().

    The interval is measured from the start of each fetch, so a slow fetch does
    not stretch the period. After a failure it retries after `retry_interval`,
    doubling each time up to `interval`: quick pickup of a slow-starting API
    without piling requests onto one that is struggling.
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
            started = time.monotonic()
            try:
                self._deliver(self._fetch())
                wait = max(0.5, self._interval - (time.monotonic() - started))
                if failures:
                    log.info("data source is back after %d failed attempt(s)", failures)
                failures = 0
            except Exception as exc:
                failures += 1
                if failures == 1:
                    log.warning("data fetch failed (%s); retrying in %ss (backing off)", exc, self._retry)
                elif failures % 10 == 0:
                    log.warning("data fetch still failing after %d attempts: %s", failures, exc)
                wait = min(self._retry * 2 ** min(failures - 1, 10), self._interval)
            self._stop_event.wait(wait)

    def stop(self):
        self._stop_event.set()
