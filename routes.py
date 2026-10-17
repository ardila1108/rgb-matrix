"""YOUR BUSES. Fill this in; nothing else needs to change.

STOPS
    stop id -> walk time in minutes from your door to that stop.

CATEGORIES
    One page on the display per category, in display order.
    - "name":  shown in the header, max 7 characters
    - "color": optional (r, g, b) accent for the page
    - "buses": list of {"line": ..., "stop": ...}
               optional "walk_min" on a bus overrides the stop's walk time

The same line + stop can appear in several categories (e.g. line 24 at stop 304
going both to the center and to the beach): the API is only called once for it.
"""

STOPS = {
    "226": {"walk_min": 5},
    "304": {"walk_min": 3},
    "348": {"walk_min": 4},
    "315": {"walk_min": 6},
    "352": {"walk_min": 5},
}

CATEGORIES = [
    {"name": "CENTRO", "buses": [
        {"line": "19", "stop": "226"},
        {"line": "31", "stop": "226"},
        {"line": "36", "stop": "304"},
    ]},
    {"name": "FRENCH", "buses": [
        {"line": "24", "stop": "348"},
        {"line": "27", "stop": "315"},
        {"line": "35", "stop": "315"},
    ]},
    {"name": "GROS", "buses": [
        {"line": "31", "stop": "226"},
        {"line": "36", "stop": "304"},
        {"line": "27", "stop": "352"},
    ]},
    #{"name": "GROS", "buses": []},     # TODO: rename and fill in
    #{"name": "CAT4", "buses": []},     # TODO: rename and fill in
]
