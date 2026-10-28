"""Unit tests for weather service caching, deduplication, HTTP 429 handling, and WeatherAPI fallback.

All tests mock provider HTTP calls using unittest.mock to avoid consuming any real API quota.
"""

import threading
import time
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.weather_service import (
    CACHE_TTL_SECONDS,
    _FORECAST_CACHE,
    _map_weatherapi_code_to_wmo,
    clear_weather_cache,
    get_weather_forecast,
)


@pytest.fixture(autouse=True)
def reset_cache_state():
    """Ensure each test runs with a completely fresh in-memory cache and reset cooldown."""
    clear_weather_cache()
    yield
    clear_weather_cache()


def _mock_open_meteo_response(status_code=200, daily_dates=None, headers=None):
    """Helper to create a mocked Open-Meteo HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    if status_code == 200:
        dates = daily_dates or [date.today().isoformat()]
        resp.json.return_value = {
            "latitude": 12.3,
            "longitude": 76.65,
            "daily": {
                "time": dates,
                "weather_code": [1] * len(dates),
                "temperature_2m_max": [31.5] * len(dates),
                "temperature_2m_min": [21.0] * len(dates),
                "precipitation_probability_max": [25] * len(dates),
            },
        }
        resp.raise_for_status.return_value = None
    elif status_code == 429:
        resp.raise_for_status.side_effect = Exception("HTTP 429 Too Many Requests")
    else:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _mock_weatherapi_response(status_code=200, forecast_dates=None):
    """Helper to create a mocked WeatherAPI.com HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    if status_code == 200:
        dates = forecast_dates or [date.today().isoformat()]
        forecastday = []
        for d in dates:
            forecastday.append({
                "date": d,
                "day": {
                    "maxtemp_c": 30.2,
                    "mintemp_c": 20.4,
                    "daily_chance_of_rain": 40,
                    "condition": {
                        "text": "Patchy rain possible",
                        "code": 1063,  # Maps to WMO 61 (slight rain)
                    },
                },
            })
        resp.json.return_value = {
            "location": {"name": "Mysuru", "lat": 12.3, "lon": 76.65},
            "forecast": {"forecastday": forecastday},
        }
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_open_meteo_success_and_6hour_cache():
    """Verify primary provider success and subsequent hits served directly from cache."""
    today = date.today()
    mock_resp = _mock_open_meteo_response(200, [today.isoformat()])

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        # First call: hits Open-Meteo
        res1 = get_weather_forecast(12.3, 76.65, today, today)
        assert res1["source"] == "Open-Meteo"
        assert res1["latitude"] == 12.3
        assert res1["longitude"] == 76.65
        assert len(res1["daily"]) == 1
        assert res1["daily"][0]["date"] == today.isoformat()
        assert res1["daily"][0]["weather_code"] == 1
        assert res1["daily"][0]["temperature_max_c"] == 31.5
        assert res1["daily"][0]["temperature_min_c"] == 21.0
        assert res1["daily"][0]["precipitation_probability_max"] == 25
        assert mock_get.call_count == 1

        # Second call with identical destination and date range: must hit cache without HTTP call
        res2 = get_weather_forecast(12.3, 76.65, today, today)
        assert res2["source"] == "Open-Meteo"
        assert res2["daily"] == res1["daily"]
        assert mock_get.call_count == 1  # No additional network call made!


def test_cache_ttl_expiration():
    """Verify that cached responses are re-fetched after the 6-hour TTL expires."""
    today = date.today()
    mock_resp = _mock_open_meteo_response(200, [today.isoformat()])

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        res1 = get_weather_forecast(12.3, 76.65, today, today)
        assert mock_get.call_count == 1

        # Find the cache entry and simulate that 6 hours + 1 second have passed
        cache_key = (round(12.3, 3), round(76.65, 3), today.isoformat(), today.isoformat())
        assert cache_key in _FORECAST_CACHE
        _FORECAST_CACHE[cache_key]["expires_at"] = time.monotonic() - 1.0

        # Next call should re-fetch from upstream
        res2 = get_weather_forecast(12.3, 76.65, today, today)
        assert mock_get.call_count == 2
        assert res2["source"] == "Open-Meteo"


def test_http_429_triggers_weatherapi_fallback(monkeypatch):
    """Verify that HTTP 429 from Open-Meteo triggers WeatherAPI.com fallback."""
    monkeypatch.setenv("WEATHERAPI_KEY", "test-secret-key-12345")
    today = date.today()

    om_429 = _mock_open_meteo_response(429, headers={"Retry-After": "60"})
    wa_200 = _mock_weatherapi_response(200, [today.isoformat()])

    def mock_get(url, *args, **kwargs):
        if "open-meteo" in url:
            return om_429
        elif "weatherapi" in url:
            # Verify secret key was sent
            assert kwargs["params"]["key"] == "test-secret-key-12345"
            return wa_200
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.Client.get", side_effect=mock_get):
        result = get_weather_forecast(12.3, 76.65, today, today)

        assert result["source"] == "WeatherAPI"
        assert len(result["daily"]) == 1
        daily_item = result["daily"][0]
        assert daily_item["date"] == today.isoformat()
        assert daily_item["weather_code"] == 61  # 1063 mapped to WMO 61
        assert daily_item["temperature_max_c"] == 30.2
        assert daily_item["temperature_min_c"] == 20.4
        assert daily_item["precipitation_probability_max"] == 40


def test_schema_compatibility_between_providers(monkeypatch):
    """Ensure both providers return the exact same schema structure expected by frontend."""
    monkeypatch.setenv("WEATHERAPI_KEY", "test-key")
    today = date.today()

    required_keys = {"date", "weather_code", "temperature_max_c", "temperature_min_c", "precipitation_probability_max"}

    # 1. Open-Meteo schema test
    om_200 = _mock_open_meteo_response(200, [today.isoformat()])
    with patch("httpx.Client.get", return_value=om_200):
        om_res = get_weather_forecast(12.3, 76.65, today, today)
        assert set(om_res.keys()) == {"latitude", "longitude", "source", "daily"}
        assert set(om_res["daily"][0].keys()) == required_keys

    clear_weather_cache()

    # 2. WeatherAPI schema test
    om_429 = _mock_open_meteo_response(429)
    wa_200 = _mock_weatherapi_response(200, [today.isoformat()])
    with patch("httpx.Client.get", side_effect=[om_429, wa_200]):
        wa_res = get_weather_forecast(12.3, 76.65, today, today)
        assert set(wa_res.keys()) == {"latitude", "longitude", "source", "daily"}
        assert set(wa_res["daily"][0].keys()) == required_keys
        assert wa_res["source"] == "WeatherAPI"


def test_both_providers_fail_returns_stale_cache(monkeypatch):
    """Verify that when both providers fail, a stale cached entry is returned and clearly labelled."""
    monkeypatch.setenv("WEATHERAPI_KEY", "test-key")
    today = date.today()

    # Seed the cache with an earlier successful Open-Meteo response
    om_200 = _mock_open_meteo_response(200, [today.isoformat()])
    with patch("httpx.Client.get", return_value=om_200):
        initial = get_weather_forecast(12.3, 76.65, today, today)
        assert initial["source"] == "Open-Meteo"

    # Expire the cache entry
    cache_key = (round(12.3, 3), round(76.65, 3), today.isoformat(), today.isoformat())
    _FORECAST_CACHE[cache_key]["expires_at"] = time.monotonic() - 10.0

    # Now both providers fail
    om_429 = _mock_open_meteo_response(429)
    wa_500 = _mock_weatherapi_response(500)

    with patch("httpx.Client.get", side_effect=[om_429, wa_500]):
        stale_res = get_weather_forecast(12.3, 76.65, today, today)
        assert "stale" in stale_res["source"].lower()
        assert stale_res.get("is_stale") is True
        assert len(stale_res["daily"]) == 1
        assert stale_res["daily"][0]["date"] == today.isoformat()


def test_both_providers_fail_no_cache_raises_runtime_error(monkeypatch):
    """Verify controlled RuntimeError when both providers fail and no stale cache exists."""
    monkeypatch.setenv("WEATHERAPI_KEY", "test-key")
    today = date.today()

    om_429 = _mock_open_meteo_response(429)
    wa_500 = _mock_weatherapi_response(500)

    with patch("httpx.Client.get", side_effect=[om_429, wa_500]):
        with pytest.raises(RuntimeError, match="temporarily unavailable from all providers"):
            get_weather_forecast(12.3, 76.65, today, today)


def test_missing_weatherapi_key_handles_gracefully(monkeypatch):
    """Verify that missing WEATHERAPI_KEY doesn't crash but skips fallback and raises controlled error."""
    monkeypatch.delenv("WEATHERAPI_KEY", raising=False)
    today = date.today()

    om_429 = _mock_open_meteo_response(429)

    with patch("httpx.Client.get", return_value=om_429) as mock_get:
        with pytest.raises(RuntimeError, match="temporarily unavailable"):
            get_weather_forecast(12.3, 76.65, today, today)
        # Only Open-Meteo was called; WeatherAPI was not called because key is missing
        assert mock_get.call_count == 1


def test_weatherapi_date_beyond_free_plan_window(monkeypatch):
    """Verify that requested dates beyond the 3-day free tier window are not queried or fabricated."""
    monkeypatch.setenv("WEATHERAPI_KEY", "test-key")
    today = date.today()
    far_future = today + timedelta(days=5)

    om_429 = _mock_open_meteo_response(429)

    with patch("httpx.Client.get", return_value=om_429) as mock_get:
        with pytest.raises(RuntimeError, match="temporarily unavailable"):
            get_weather_forecast(12.3, 76.65, far_future, far_future)
        # WeatherAPI was skipped because day 5 is outside free 3-day horizon
        assert mock_get.call_count == 1


def test_simultaneous_requests_deduplicated():
    """Verify that concurrent requests for the same destination & dates are deduplicated upstream."""
    today = date.today()
    mock_resp = _mock_open_meteo_response(200, [today.isoformat()])
    call_counter = 0

    def slow_mock_get(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        time.sleep(0.15)  # simulate slow network call
        return mock_resp

    results = []

    def worker():
        res = get_weather_forecast(12.3, 76.65, today, today)
        results.append(res)

    with patch("httpx.Client.get", side_effect=slow_mock_get):
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # All 5 threads received valid responses
    assert len(results) == 5
    for r in results:
        assert r["source"] == "Open-Meteo"
    # But only 1 upstream network request was made!
    assert call_counter == 1


def test_condition_code_mapping():
    """Verify condition codes are accurately mapped from WeatherAPI to WMO."""
    assert _map_weatherapi_code_to_wmo(1000) == 0   # Sunny -> Clear
    assert _map_weatherapi_code_to_wmo(1003) == 1   # Partly cloudy -> Mainly clear
    assert _map_weatherapi_code_to_wmo(1009) == 3   # Overcast -> Overcast
    assert _map_weatherapi_code_to_wmo(1030) == 45  # Mist -> Fog
    assert _map_weatherapi_code_to_wmo(1087) == 95  # Thunder -> Thunderstorm
    assert _map_weatherapi_code_to_wmo(1186) == 63  # Moderate rain
    assert _map_weatherapi_code_to_wmo(1225) == 75  # Heavy snow
    assert _map_weatherapi_code_to_wmo(9999) == 2   # Unknown code -> default 2
