"""Fake data that counts down fast, so every color state shows up."""
import time

SECONDS_PER_MINUTE = 3   # demo clock runs 20x faster than real time

# page name -> [(line, starting minutes, walk minutes), ...]
_DEMO = {
    "CITY": [("24", 12, 4), ("9", 6, 3), ("132", 20, 5), ("N3", 9, 4)],
    "AIRPORT": [("7", 25, 3), ("41", 14, 4), ("88", 22, 5)],
    "BEACH": [("15", 18, 3), ("33", 10, 4), ("61", 27, 5)],
    "STATION": [("2", 8, 5), ("12", 16, 3), ("50", 20, 4)],
}
_CYCLE = 28


def fetch_pages():
    tick = int(time.time() / SECONDS_PER_MINUTE)
    pages = []
    for name, buses in _DEMO.items():
        pages.append({
            "name": name,
            "buses": [
                {"line": line, "minutes": (start - tick) % _CYCLE, "walk_min": walk}
                for line, start, walk in buses
            ],
        })
    return pages
