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
