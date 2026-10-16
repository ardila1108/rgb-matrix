"""Your real data. Fill in fetch_pages() and you're done."""


def fetch_pages():
    """Return the current snapshot as a list of pages:

    [
      {"name": "CITY",                      # max 7 chars, shown in the header
       "buses": [
         {"line": "24", "minutes": 12, "walk_min": 4},
         {"line": "9",  "minutes": 6,  "walk_min": 3},
       ]},
      {"name": "AIRPORT", "color": (255, 80, 200), "buses": [...]},   # color optional
    ]

    Page order = display order. If this raises, the screen keeps showing the
    last good snapshot and the progress line turns dim red once it goes stale.
    """
    raise NotImplementedError("Implement fetch_pages() in ledwall/data_sources/live.py")
