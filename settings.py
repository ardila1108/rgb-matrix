"""All tunable settings live here. Edit, commit, push: the Pi picks it up."""
import os

# --- Runtime -------------------------------------------------------------
# "simulator" = browser preview (PC), "hardware" = the real panel (Pi).
# docker-compose files set these through env vars; the defaults are for the PC.
BACKEND = os.environ.get("LED_BACKEND") or "simulator"
# "demo" = fake countdown data, "live" = ledwall/data_sources/live.py
# Use LED_DATA=demo for the fake countdown data.
DATA_SOURCE = os.environ.get("LED_DATA") or "live"
# Which screen is shown: "bus" or "test" (panel test patterns).
SCREEN = os.environ.get("LED_SCREEN") or "clock"      # screen shown at startup
MENU_SCREENS = ("bus", "clock")     # buttons on the phone page ("test" is only for LED_SCREEN=test)
CONTROL_PORT = 8080                 # phone page: http://<pi-ip>:8080
TIMEZONE = "Europe/Madrid"          # clock screen
TEST_SECONDS_PER_PATTERN = 4
FPS = 20
SIMULATOR_PORT = 8000

# --- Matrix (copied from the hello-world script that works on your Pi) -----
ROWS = 64
COLS = 64
HARDWARE_MAPPING = "regular"        # "adafruit-hat" only for a real Bonnet wiring
DISABLE_HARDWARE_PULSING = True
GPIO_SLOWDOWN = 4                # None = library default; flicker/noise -> try 2-4
BRIGHTNESS = 80                     # 1-100
# Flicker tuning (None = library default). See README "Flicker".
PWM_BITS = None                     # lower (e.g. 9 or 8) = faster refresh, fewer color shades
LIMIT_REFRESH_HZ = None             # e.g. 120: steadier timing, less flicker from load
PWM_LSB_NANOSECONDS = None          # lower (e.g. 100) = faster refresh

# --- Live data: the dbus-api container ---------------------------------------
# Inside docker compose "dbus-api" is the service name. "localhost" would be the
# led-wall container itself. Without Docker use LED_API_URL=http://localhost:3000
API_BASE_URL = os.environ.get("LED_API_URL") or "http://dbus-api:3000"
API_CONNECT_TIMEOUT_SECONDS = 3     # API container not reachable: fail fast and retry
API_TIMEOUT_SECONDS = 20            # max wait for an answer (the API scrapes a website, so it is slow)
API_MAX_WORKERS = 2                 # parallel requests per refresh; keep low, the API scrapes per request
API_REUSE_SECONDS = 90              # a failed request keeps its last good value this long

# --- Data ------------------------------------------------------------------
POLL_SECONDS = 20                   # how often the data source is asked
FAILURE_RETRY_SECONDS = 3           # first retry after a failed fetch; doubles up to POLL_SECONDS
LOCAL_COUNTDOWN = False              # tick minutes down between API refreshes
STALE_AFTER_SECONDS = 120           # no fresh data for this long -> red progress line

# --- Bus screen: paging ----------------------------------------------------
DWELL_SECONDS = 3
TRANSITION_SECONDS = 0.3
MAX_PAGE_NAME_CHARS = 7             # header fits 7 chars
MAX_LINE_CHARS = 3                  # badge fits 3 chars
DOT_BLINK = False                   # page dots: False = steady color, True = blink
# Page dots light with the first state in this list that a page has a bus in.
# Names: "leave" (purple), "ready" (amber), "run" (orange), "gone" (red), "relax" (green).
DOT_PRIORITY = ("leave", "ready", "gone")
MAX_MINUTES_SHOWN = 60              # buses further away than this are hidden (display max: 99)

# --- Bus screen: urgency rules (slack = minutes left - walk minutes) --------
GONE_MINUTES = 1                    # this many minutes or less -> red, blinking
LEAVE_NOW_SLACK = (0, 1)            # violet: last chance without running
GET_READY_SLACK = (2, 3)            # amber
UNREACHABLE_SLACK = -2              # slack below this -> gray (can't make it)
# slack above GET_READY_SLACK[1] -> green; slack below LEAVE_NOW_SLACK[0] -> orange

# --- Bus screen: colors (R, G, B) ------------------------------------------
COLOR_RELAX = (0, 220, 90)
COLOR_READY = (255, 190, 0)
COLOR_LEAVE = (190, 80, 255)
COLOR_RUN = (255, 100, 0)
COLOR_GONE = (255, 30, 30)
COLOR_UNREACHABLE = (90, 90, 90)
COLOR_BADGE = (40, 90, 230)
COLOR_TEXT = (255, 255, 255)
COLOR_UNIT = (170, 170, 170)
COLOR_DOT_OFF = (45, 45, 45)
COLOR_STALE = (120, 0, 0)
# Header accent per page (arrow + progress line), used in order unless a page
# dict has its own "color".
PAGE_COLORS = [(0, 200, 255), (210, 210, 210), (90, 130, 255), (210, 170, 120)]
