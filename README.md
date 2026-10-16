# led-wall

Multi-screen display for a 64x64 RGB LED matrix (Raspberry Pi 4 + Adafruit Bonnet).
First screen: bus times, paged by destination, colored by how much time you have
after the walk to the stop.

## Layout

```
settings.py                 every tunable value (screen, matrix, timing, colors, rules)
run.py                      entry point
ledwall/
  screens/base.py           Screen interface (update(data), render(now) -> image)
  screens/bus.py            BusScreen: pages, header, dots, rows, transitions
  screens/bus_logic.py      pure logic: classify(), prepare_pages()
  screens/test.py           TestScreen: panel test patterns
  manager.py                ScreenManager: holds screens, picks the active one
  backends.py               HardwareBackend (Pi) / SimulatorBackend (browser)
  data_sources/live.py      <- implement fetch_pages() here
  data_sources/demo.py      fake data that cycles through every color state
  poller.py                 calls fetch_pages() every POLL_SECONDS
deploy/deploy.sh            manual update script for the Pi
```

Adding a screen later: subclass `Screen`, register it in `ledwall/main.py`'s
`ScreenManager([...])`. Switching logic goes in `manager.py`.

## Data shape (what fetch_pages() returns)

```python
[{"name": "CITY",                       # max 7 chars
  "buses": [{"line": "24", "minutes": 12, "walk_min": 4}]},
 {"name": "AIRPORT", "color": (255, 80, 200), "buses": [...]}]   # color optional
```

## Develop on the PC

```
docker compose up                 # http://localhost:8000 (simulator + demo data)
docker compose run --rm test      # pytest
```
Code is mounted into the container: edit, then `docker compose restart led-wall`.
No Docker needed either: `pip install -r requirements-dev.txt`, then `python run.py`
or `pytest -k <name>`.

To use your real data, implement `ledwall/data_sources/live.py` and set
`DATA_SOURCE = "live"` in `settings.py`.

## Choosing the screen / panel test patterns

In `settings.py`, change `"bus"` to `"test"` in the `SCREEN = ...` line, then deploy.
The test screen shows color bars, a grid with colored corners and a TOP label,
sweeping lines, and full-screen R/G/B/white. `LED_SCREEN=test` is a shortcut for
one-off runs: `LED_SCREEN=test docker compose up` (PC) or
`LED_SCREEN=test docker compose -f docker-compose.pi.yml up --build` (Pi).

## Set up the Pi (once)

1. Solder-bridge the E-line jumper on the Bonnet (needed for 64x64).
2. Add `dtparam=audio=off` to `/boot/firmware/config.txt`, reboot.
3. Install Docker (includes `docker compose`): `curl -fsSL https://get.docker.com | sh`,
   then `sudo usermod -aG docker $USER` and log in again.
4. Give the Pi read access to the repo. For a private repo: `ssh-keygen -t ed25519`,
   add `~/.ssh/id_ed25519.pub` in GitHub > repo > Settings > Deploy keys (read-only),
   and clone with the SSH URL.
5. `git clone <repo-ssh-url> ~/led-wall && cd ~/led-wall && ./deploy/deploy.sh development`

The first build takes a few minutes. The container restarts itself after a reboot.

## Day to day

Push to `development`, then update the Pi over SSH:

```
ssh pi@raspberrypi.local 'cd ~/led-wall && ./deploy/deploy.sh development'
```

- Approved: merge to `main`, then `./deploy/deploy.sh main`.
- Rollback: `./deploy/deploy.sh v1.0` (any tag works).
- No argument = the last branch you deployed.
- App logs: `docker compose -f docker-compose.pi.yml logs -f`
- Stop the display: `docker compose -f docker-compose.pi.yml down`
- A value tweaked directly on the Pi is reset by the next deploy; copy keepers back to the PC.
