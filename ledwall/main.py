import logging
import os
import time

import settings
from .backends import make_backend
from .automation import Automation, build_schedule
from .control import ControlServer
from .frames import FrameGate
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

    try:
        schedule = build_schedule(known_screens=["bus", "clock", "weather", "freestyle", "test"])
    except ValueError as exc:
        log.error("%s", exc)
        raise SystemExit(1)

    # The bus screen is always fed, so it is up to date whenever you switch to it.
    fetch, interval = make_fetch()
    poller = Poller(fetch, bus.update, interval, retry_interval=settings.FAILURE_RETRY_SECONDS)
    poller.start()

    weather_fetch, weather_interval = make_weather_fetch()
    weather_poller = Poller(weather_fetch, weather.update, weather_interval,
                            retry_interval=settings.FAILURE_RETRY_SECONDS)
    weather_poller.start()

    # Showing the test patterns means you are checking the panel: no schedule then.
    automation = Automation(schedule, manager, display=backend,
                            enabled=settings.AUTOMATION and settings.SCREEN != "test",
                            state_path=os.path.join(settings.DATA_DIR, "state.json"))
    automation.tick()                                   # right screen and brightness from frame one

    control = ControlServer(manager, settings.MENU_SCREENS, settings.CONTROL_PORT,
                            display=backend, automation=automation)
    control.start()

    log.info("running: screen=%s backend=%s data=%s", settings.SCREEN, settings.BACKEND, settings.DATA_SOURCE)
    log.info("phone page at http://<this-machine>:%d", settings.CONTROL_PORT)
    if settings.BACKEND == "simulator":
        log.info("preview at http://localhost:%d", settings.SIMULATOR_PORT)

    gate = FrameGate()
    try:
        while True:
            start = time.monotonic()
            automation.tick()
            image = manager.render(start)
            if gate.changed(image, backend.brightness):      # unchanged frames are not re-sent
                backend.show(image)
            time.sleep(max(0.0, 1.0 / manager.fps - (time.monotonic() - start)))
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
