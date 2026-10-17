import logging
import time

import settings
from .backends import make_backend
from .manager import ScreenManager
from .poller import Poller
from .screens import BusScreen, TestScreen

log = logging.getLogger("ledwall")


def make_fetch():
    if settings.DATA_SOURCE == "demo":
        from .data_sources.demo import fetch_pages
        return fetch_pages, 1.0                 # demo data changes every second
    if settings.DATA_SOURCE == "live":
        from .data_sources import live
        live.check_routes()                     # fail early with a clear message
        return live.fetch_pages, settings.POLL_SECONDS
    raise ValueError(f"unknown DATA_SOURCE: {settings.DATA_SOURCE!r}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    backend = make_backend()
    bus = BusScreen()
    manager = ScreenManager([bus, TestScreen()], active=settings.SCREEN)

    poller = None
    if settings.SCREEN == "bus":              # the test screen needs no data
        fetch, interval = make_fetch()
        poller = Poller(fetch, bus.update, interval, retry_interval=settings.FAILURE_RETRY_SECONDS)
        poller.start()
    log.info("running: screen=%s backend=%s data=%s", settings.SCREEN, settings.BACKEND, settings.DATA_SOURCE)
    if settings.BACKEND == "simulator":
        log.info("preview at http://localhost:%d", settings.SIMULATOR_PORT)

    frame = 1.0 / settings.FPS
    try:
        while True:
            start = time.monotonic()
            backend.show(manager.render(start))
            time.sleep(max(0.0, frame - (time.monotonic() - start)))
    except KeyboardInterrupt:
        pass
    finally:
        if poller:
            poller.stop()
        backend.close()


if __name__ == "__main__":
    main()
