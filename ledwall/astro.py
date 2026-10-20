"""Sun and moon, computed offline (no network, no API key)."""
import math
from datetime import date, datetime, timedelta, timezone

SYNODIC_MONTH = 29.530588853          # days between new moons
_NEW_MOON_JD = 2451550.1              # a mean new moon (January 2000)
_UNIX_EPOCH_JD = 2440587.5

PHASE_NAMES = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous",
               "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]


def julian_day(moment: datetime) -> float:
    return moment.astimezone(timezone.utc).timestamp() / 86400.0 + _UNIX_EPOCH_JD


def moon_phase(moment: datetime) -> float:
    """0 = new moon, 0.25 = first quarter, 0.5 = full moon, 0.75 = last quarter.

    Uses the mean lunar cycle: within about a day of the true phase,
    which is plenty for a 9-pixel moon.
    """
    return ((julian_day(moment) - _NEW_MOON_JD) / SYNODIC_MONTH) % 1.0


def moon_illumination(phase: float) -> float:
    """Share of the disc that is lit, 0..1."""
    return (1 - math.cos(2 * math.pi * phase)) / 2


def moon_name(phase: float) -> str:
    return PHASE_NAMES[int(phase * 8 + 0.5) % 8]


def sun_times(day: date, latitude: float, longitude: float, tz):
    """(sunrise, sunset) as aware datetimes in `tz`, or None in polar day/night.

    The standard sunrise equation; accurate to about two minutes.
    """
    sin = lambda deg: math.sin(math.radians(deg))
    cos = lambda deg: math.cos(math.radians(deg))

    jd_noon_utc = day.toordinal() + 1721425.0           # 12:00 UTC of that date
    n = round(jd_noon_utc - 2451545.0)
    j_star = n - longitude / 360.0                      # mean solar time at this longitude (east positive)
    m = (357.5291 + 0.98560028 * j_star) % 360
    c = 1.9148 * sin(m) + 0.02 * sin(2 * m) + 0.0003 * sin(3 * m)
    lam = (m + c + 180 + 102.9372) % 360                # ecliptic longitude
    j_transit = 2451545.0 + j_star + 0.0053 * sin(m) - 0.0069 * sin(2 * lam)
    sin_decl = sin(lam) * sin(23.4397)
    cos_decl = math.sqrt(1 - sin_decl ** 2)
    cos_omega = (sin(-0.833) - sin(latitude) * sin_decl) / (cos(latitude) * cos_decl)
    if not -1 <= cos_omega <= 1:
        return None
    omega = math.degrees(math.acos(cos_omega))

    def to_datetime(jd):
        utc = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - _UNIX_EPOCH_JD)
        return utc.astimezone(tz)

    return to_datetime(j_transit - omega / 360), to_datetime(j_transit + omega / 360)
