# led-wall

Multi-screen display for a 64x64 RGB LED matrix (Raspberry Pi 4 + Adafruit Bonnet).
First screen: bus times, paged by destination, colored by how much time you have
after the walk to the stop.

## Layout

```
routes.py                   <- YOUR buses: stops, walk times, categories
settings.py                 every tunable value (screen, matrix, timing, colors, rules)
run.py                      entry point
ledwall/
  screens/base.py           Screen interface (update(data), render(now) -> image)
  screens/bus.py            BusScreen: pages, header, dots, rows, transitions
  screens/bus_logic.py      pure logic: classify(), prepare_pages()
  screens/clock.py          ClockScreen: time and date in Spain
  screens/weather.py        WeatherScreen: weather, rain chances, sun and moon
  screens/halloween.py      HalloweenScreen: pumpkins, ghosts, bats, a dancing skeleton
  halloween_art.py          the pixel art for it, drawn with code
  screens/freestyle.py      FreestyleScreen: a canvas you sketch on from the phone
  screens/test.py           TestScreen: panel test patterns
  draw_page.py              the sketch page (/draw)
  control.py                phone page + API to switch screens, brightness, automation
  automation.py             schedule: which screen and brightness by time of day
  manager.py                ScreenManager: holds screens, picks the active one
  backends.py               HardwareBackend (Pi) / SimulatorBackend (browser)
  data_sources/live.py      calls the dbus-api container, builds the pages
  data_sources/demo.py      fake data that cycles through every color state
  data_sources/weather.py   Open-Meteo weather (free, no key); weather_demo.py = fake scenes
  astro.py                  sunrise/sunset and moon phase, computed offline
  icons.py                  pixel-art sun, moon with phase, clouds, rain, snow
  poller.py                 calls fetch_pages() every POLL_SECONDS
deploy/deploy.sh            manual update script for the Pi
```

Adding a screen later: subclass `Screen`, register it in `ledwall/main.py`'s
`ScreenManager([...])`. Switching logic goes in `manager.py`.

## Automation (settings.py)

The panel can run itself by time of day. Defaults, matching a typical day:

```python
DEFAULT_SCREENS = ("clock", "weather", "halloween")   # rotate, ROTATION_SECONDS (20) each
SCREEN_SCHEDULE = [
    {"from": "08:00", "to": "11:00", "screens": ("bus",)},     # one screen = always that one
    {"from": "16:00", "to": "19:00", "screens": ("bus",)},
]
BRIGHTNESS_SCHEDULE = [{"from": "23:00", "to": "07:00", "brightness": 10}]   # else BRIGHTNESS
```

- The first matching window wins. "from" is included, "to" is not; windows may cross midnight.
- Per window you can add `"days": ("mon", "tue", "wed", "thu", "fri")`, `"seconds": 30`, and per
  screen `("weather", 45)`. A window can rotate any screens: `("clock", "weather", "bus")`.
- Mistakes (bad times, unknown screens, brightness outside 1-100) are all listed in the log at
  startup, and the tests check the shipped schedule.
- **Brightness** changes only when a window starts or ends. A slider move on the phone stays until
  the next scheduled change, and the schedule is applied right at startup.
- **Picking a screen by hand** pauses the screen schedule for `MANUAL_HOLD_MINUTES` (30; 0 = until
  you tap Resume). Drawing keeps renewing the pause. The phone page has an Automation switch,
  shows what is running and until when, and a Resume button while a pause is active.
- With `SCREEN = "test"` (panel test patterns) automation starts off. `AUTOMATION = False` turns
  it off at startup; after a restart it returns to what `settings.py` says.

## Switching screens from your phone

Open `http://<pi-ip>:8080` (on your PC: `http://localhost:8080`) on the same Wi-Fi and tap a
screen. Give the Pi a fixed IP in your router so the address does not change. Add the page
to your phone's home screen to use it like an app. There is no login: keep the port on your
home network only. After a restart the panel starts on `SCREEN` from `settings.py`.
Below the screen buttons there is a **Brightness** slider (5-100%) with Night / Dim / Day / Max
presets: it changes the panel live. `BRIGHTNESS` in `settings.py` is the value at startup, so
after a restart or deploy the panel returns to it. Buttons shown: `MENU_SCREENS`. The **Draw** button opens the sketch page: pen, eraser, fill,
brush sizes, colors, undo, clear. Strokes appear on the panel as you draw, and the sketch is
kept in `DATA_DIR` (a Docker volume on the Pi), so it survives restarts and deploys. Clock timezone: `TIMEZONE`.

## Halloween screen

A little night show in four short acts, one act per visit: HAPPY HALLOWEEN typed out with a
pumpkin popping up and ghosts drifting in; a pumpkin patch with a ghost gliding past and eyes
blinking in the dark; a graveyard where a skeleton climbs out of the ground and dances; and a
haunted moon with bats, a spider on a thread and a BOO! Each time the screen comes back in the
rotation it plays the next act from its beginning.

It is part of the default rotation: `DEFAULT_SCREENS = ("clock", "weather", "halloween")`.
To change that, edit the list in `settings.py`:

```python
DEFAULT_SCREENS = ("clock", "weather", ("halloween", 40))   # give it 40 s instead of 20
DEFAULT_SCREENS = ("clock", "weather")                       # after Halloween: take it out
```
`HALLOWEEN_ACT_SECONDS` (10) is the length of each act. You can also put it in a window of
`SCREEN_SCHEDULE`, for example every evening 18:00-23:00, or pin it with the 📌 button.

## Weather screen

Top: weather icon, temperature, today's high/low. Middle: rain chance for the next 12 hours
(one bar per hour). Bottom: the 24 hours as a colored strip with a marker for now, sunrise and
sunset times, and a small moon showing **today's phase**. On a clear night the big icon is the
moon with its phase too. A pulsing blue border means rain is likely soon
(`RAIN_ALERT_PERCENT` within `RAIN_ALERT_HOURS`).

Set `LATITUDE` / `LONGITUDE` in `settings.py` to your street. Weather comes from Open-Meteo every
`WEATHER_POLL_SECONDS` (10 min); sunrise, sunset and the moon are computed on the Pi, so the
bottom strip works even with no internet. With `LED_DATA=demo` the screen cycles through fake
scenes (sun, rain, fog, snow, storm, night) so you can see every look.

## Page dots

Top right, one dot per page. The page on screen is white. Other pages light with the first
state in `DOT_PRIORITY` (`settings.py`) that they have a bus in. Default order: **purple**
(leave now), **amber** (get ready), **red** (gone). Add `"run"` (orange) or `"relax"`
(green) to the list if you want those too. `DOT_BLINK = True` makes the dots blink instead
of staying lit.

## Old bus data

If no fresh bus data arrives for `STALE_AFTER_SECONDS` (2 minutes), the minutes are no longer
trusted: the rows show gray `--` and the line under the header turns red. They come back by
themselves as soon as data arrives again.

## Your buses (routes.py)

```python
STOPS = {"304": {"walk_min": 4}}                      # stop id -> walk minutes from your door
CATEGORIES = [                                        # one page each, in order
  {"name": "CITY", "buses": [{"line": "24", "stop": "304"}]},
  {"name": "BEACH", "buses": [{"line": "24", "stop": "304"}]},   # same bus in 2 categories is fine
]
```
Buses further away than `MAX_MINUTES_SHOWN` (default 60, in `settings.py`) are hidden, and a page
with no buses left is skipped.
Optional: `"color": (r, g, b)` per category, `"walk_min"` per bus. Each unique line+stop
is requested once per refresh (every `POLL_SECONDS`, in parallel). `routes.py` is checked at
startup and by the tests, with plain-language messages if something is missing.

The API runs as the `dbus-api` service in compose. Inside compose the screen reaches it at
`http://dbus-api:3000` (`localhost` would be the led-wall container itself). Without Docker:
`LED_API_URL=http://localhost:3000 python run.py`. Fake data instead: `LED_DATA=demo`.
A failed request keeps the last good value for `API_REUSE_SECONDS`; if every request fails,
the screen keeps its last snapshot and the progress line turns dim red once it is stale.

## Develop on the PC

```
docker compose up                 # http://localhost:8000 (simulator + demo data)
docker compose run --rm test      # pytest
```
Code is mounted into the container: edit, then `docker compose restart led-wall`.
No Docker needed either: `pip install -r requirements-dev.txt`, then `python run.py`
or `pytest -k <name>`.


## Choosing the screen / panel test patterns

In `settings.py`, change `"bus"` to `"test"` in the `SCREEN = ...` line, then deploy.
The test screen shows color bars, a grid with colored corners and a TOP label,
sweeping lines, and full-screen R/G/B/white. `LED_SCREEN=test` is a shortcut for
one-off runs: `LED_SCREEN=test docker compose up` (PC) or
`LED_SCREEN=test docker compose -f docker-compose.pi.yml up --build` (Pi).

## Set up the Pi (once)

1. Match the wiring settings to what works on your panel (`HARDWARE_MAPPING`, etc. in `settings.py`). If you use an Adafruit Bonnet, solder-bridge the E-line jumper (needed for 64x64).
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

## Flicker

The panel needs a CPU core almost all the time (30-40% of one). The library runs its refresh on
**core 3** at top priority. Anything else that lands on core 3, or software timing instead of the
hardware pulse generator, shows up as brightness flicker. Try these in order, one at a time:

1. **Hardware pulsing** (usually the biggest one). The library says that without it you get
   "random brightness glitches". It needs the sound module gone. Check: `lsmod | grep snd_bcm2835`
   must print nothing. If it prints something:
   ```
   cat <<EOF | sudo tee /etc/modprobe.d/blacklist-rgb-matrix.conf
   blacklist snd_bcm2835
   EOF
   sudo update-initramfs -u
   sudo reboot
   ```
   Then set `DISABLE_HARDWARE_PULSING = False` in `settings.py`. If the sound module is still
   loaded the library refuses to start, and the log says so. This needs the panel's OE line on
   GPIO 18, which is what the `regular` mapping uses.
2. **Reserve core 3.** Add this to the end of the single line in `/boot/firmware/cmdline.txt`
   (same line, no newline), then reboot:
   ```
   isolcpus=domain,managed_irq,3 nohz_full=3 rcu_nocbs=3 irqaffinity=0,1,2
   ```
   Check: `cat /sys/devices/system/cpu/isolated` prints `3`.
3. **Already done by the app:** `APP_CPUS` keeps our own threads off core 3, the `dbus-api` service
   is limited to cores 0-2 in the compose files, and frames that did not change are not re-sent
   (a clock or weather screen is redrawn 4 times a second, not 20).
4. **Steady refresh rate.** Set `SHOW_REFRESH_RATE = True`, watch `docker compose logs -f led-wall`
   for a minute, then set `LIMIT_REFRESH_HZ` a little below the lowest value you saw. A fixed rate
   hides the small slowdowns that look like flicker.
5. **Faster refresh:** `PWM_BITS = 9` (then 8), `PWM_LSB_NANOSECONDS = 100`. Fewer shades, faster scan.
6. **Brightness:** low values flicker more. Try the slider at 100% and at 10%. If only the low end
   flickers, raise the night value in `BRIGHTNESS_SCHEDULE`.
7. **Who is using the CPU?** `docker stats --no-stream` while it flickers. If `dbus-api` is high
   (a Chrome fallback shows as 100%+), fix that first. To test the panel alone, stop everything and
   run your small hello-world script with the same options: if that flickers too, it is wiring,
   power supply, or the options above; if not, something else is using the CPU.
