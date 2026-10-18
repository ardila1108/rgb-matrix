import threading

from ledwall.poller import Poller


def test_retries_quickly_after_failure_then_waits_full_interval():
    calls, got = [], []
    ready = threading.Event()

    def fetch():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("api not up yet")
        return ["data"]

    def deliver(data):
        got.append(data)
        ready.set()

    p = Poller(fetch, deliver, interval=100, retry_interval=0.01)
    p.start()
    assert ready.wait(2), "poller should recover within retry time, not the 100 s interval"
    p.stop()
    assert len(calls) == 3 and got == [["data"]]


def test_failures_back_off_up_to_the_interval():
    waits = []

    class FakeEvent:
        def is_set(self):
            return len(waits) >= 6

        def wait(self, seconds):
            waits.append(seconds)

        def set(self):
            pass

    def fetch():
        raise ConnectionError("down")

    p = Poller(fetch, lambda d: None, interval=10, retry_interval=1)
    p._stop_event = FakeEvent()
    p.run()
    assert waits == [1, 2, 4, 8, 10, 10]


def test_success_wait_is_measured_from_fetch_start():
    waits = []

    class FakeEvent:
        def is_set(self):
            return len(waits) >= 1

        def wait(self, seconds):
            waits.append(seconds)

        def set(self):
            pass

    p = Poller(lambda: [], lambda d: None, interval=20)
    p._stop_event = FakeEvent()
    p.run()
    assert 19 < waits[0] <= 20
