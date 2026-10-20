import pytest

import settings
from ledwall.data_sources.weather import classify_weather, fetch_weather, parse_forecast


@pytest.mark.parametrize("code,kind", [
    (0, "clear"), (1, "clear"), (2, "partly"), (3, "cloudy"), (45, "fog"), (48, "fog"),
    (51, "rain"), (61, "rain"), (65, "rain"), (80, "rain"), (82, "rain"),
    (71, "snow"), (75, "snow"), (86, "snow"), (95, "storm"), (99, "storm"),
    (1234, "cloudy"),                                    # unknown codes fall back to clouds
])
def test_weather_codes_map_to_icon_families(code, kind):
    assert classify_weather(code) == kind


def payload(now="2026-10-19T14:15", temp=18.4, probs=None, hi=21.6, lo=12.2):
    times = [f"2026-10-{19 + h // 24}T{h % 24:02d}:00" for h in range(48)]
    probs = list(range(0, 96, 2)) if probs is None else probs       # 0, 2, 4, ... one per hour
    return {
        "current": {"time": now, "temperature_2m": temp, "weather_code": 3, "is_day": 1},
        "hourly": {"time": times, "precipitation_probability": probs},
        "daily": {"time": ["2026-10-19", "2026-10-20"],
                  "temperature_2m_max": [hi, 20.0], "temperature_2m_min": [lo, 11.0]},
    }


def test_parse_forecast_basic_fields_and_rounding():
    data = parse_forecast(payload())
    assert (data["temp"], data["hi"], data["lo"]) == (18, 22, 12)
    assert data["code"] == 3 and data["is_day"] is True


def test_rounding_goes_half_up_and_handles_negatives():
    assert parse_forecast(payload(temp=18.5))["temp"] == 19
    assert parse_forecast(payload(temp=-3.4))["temp"] == -3
    assert parse_forecast(payload(temp=-0.4))["temp"] == 0


def test_rain_starts_at_the_current_hour_and_covers_twelve_hours():
    data = parse_forecast(payload(now="2026-10-19T14:15"))
    assert data["rain"] == [28 + 2 * i for i in range(12)]            # hours 14..25
    assert parse_forecast(payload(now="2026-10-19T00:05"))["rain"][0] == 0


def test_missing_probabilities_become_zero_and_short_lists_are_padded():
    probs = [None] * 46 + [40, 50]                                   # only 2 hours left at the end
    data = parse_forecast(payload(now="2026-10-20T22:30", probs=probs))
    assert data["rain"] == [40, 50] + [0] * 10
    assert parse_forecast(payload(probs=[None] * 48))["rain"] == [0] * 12


def test_incomplete_payloads_raise():
    broken = payload()
    del broken["current"]["weather_code"]
    with pytest.raises(KeyError):
        parse_forecast(broken)


def test_fetch_sends_the_right_request():
    seen = {}

    class Resp:
        def raise_for_status(self):
            seen["checked"] = True

        def json(self):
            return payload()

    def fake_get(url, params, timeout):
        seen.update(url=url, params=params, timeout=timeout)
        return Resp()

    data = fetch_weather(get=fake_get)
    assert data["temp"] == 18 and seen["checked"]
    assert seen["url"] == settings.WEATHER_API_URL
    assert seen["params"]["latitude"] == settings.LATITUDE
    assert seen["params"]["longitude"] == settings.LONGITUDE
    assert seen["params"]["timezone"] == settings.TIMEZONE
    assert "weather_code" in seen["params"]["current"] and "is_day" in seen["params"]["current"]
    assert seen["params"]["hourly"] == "precipitation_probability"
    assert isinstance(seen["timeout"], tuple)
