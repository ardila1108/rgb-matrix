import logging
import os
import time

import settings
from .backends import make_backend
from .control import ControlServer
from .manager import ScreenManager
from .poller import Poller
from .screens import BusScreen, ClockScreen, FreestyleScreen, TestScreen, WeatherScreen

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


def make_weather_fetch():
    if settings.DATA_SOURCE == "demo":
        from .data_sources.weather_demo import fetch_weather
        return fetch_weather, 1.0                   # demo scenes change every few seconds
    from .data_sources.weather import fetch_weather
    return fetch_weather, settings.WEATHER_POLL_SECONDS


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    backend = make_backend()
    bus = BusScreen()
    sketch = FreestyleScreen(path=os.path.join(settings.DATA_DIR, "freestyle", "canvas.png"))
    weather = WeatherScreen()
    manager = ScreenManager([bus, ClockScreen(), weather, sketch, TestScreen()], active=settings.SCREEN)

    # The bus screen is always fed, so it is up to date whenever you switch to it.
    fetch, interval = make_fetch()
    poller = Poller(fetch, bus.update, interval, retry_interval=settings.FAILURE_RETRY_SECONDS)
    poller.start()

    weather_fetch, weather_interval = make_weather_fetch()
    weather_poller = Poller(weather_fetch, weather.update, weather_interval,
                            retry_interval=settings.FAILURE_RETRY_SECONDS)
    weather_poller.start()

    control = ControlServer(manager, settings.MENU_SCREENS, settings.CONTROL_PORT)
    control.start()

    log.info("running: screen=%s backend=%s data=%s", settings.SCREEN, settings.BACKEND, settings.DATA_SOURCE)
    log.info("phone page at http://<this-machine>:%d", settings.CONTROL_PORT)
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
        weather_poller.stop()
        control.stop()
        backend.close()


if __name__ == "__main__":
    main()
