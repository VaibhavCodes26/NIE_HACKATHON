"""Unit tests for Google Weather API service: caching, deduplication, condition mapping, and horizon handling.

All tests mock Google Weather API HTTP calls using unittest.mock to avoid consuming real API quota.
"""

import threading
import time
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.weather_service import (
    CACHE_TTL_SECONDS,
    _WEATHER_CACHE,
    _map_google_condition_to_wmo,
    clear_weather_cache,
    get_weather_forecast,
    FORECAST_NOTICE_TEXT,
)




@pytest.fixture(autouse=True)
def reset_cache_state():
    """Ensure each test runs with a completely fresh in-memory cache."""
    clear_weather_cache()
    yield
    clear_weather_cache()


def _make_google_day(date_obj: date, cond_type: str = "SUNNY", max_c: float = 31.5, min_c: float = 21.0, precip_pct: int = 25) -> dict:
    """Helper to build a single Google forecastDays entry."""
    return {
        "displayDate": {"year": date_obj.year, "month": date_obj.month, "day": date_obj.day},
        "maxTemperature": {"degrees": max_c, "unit": "CELSIUS"},
        "minTemperature": {"degrees": min_c, "unit": "CELSIUS"},
        "daytimeForecast": {
            "weatherCondition": {
                "type": cond_type,
                "description": {"text": cond_type.replace("_", " ").title()},
            },
            "precipitation": {"probability": {"percent": precip_pct}},
        },
    }


def _mock_google_response(status_code: int = 200, forecast_dates=None) -> MagicMock:
    """Helper to create a mocked Google Weather API HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    if status_code == 200:
        dates = forecast_dates or [date.today()]
        resp.json.return_value = {"forecastDays": [_make_google_day(d) for d in dates]}
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

def test_success_and_6hour_cache(monkeypatch):
    """Google Weather success + subsequent hits served from cache."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_resp = _mock_google_response(200, [today])

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        res1 = get_weather_forecast(12.3, 76.65, today, today)
        assert res1["source"] == "Google Weather"
        assert res1["latitude"] == 12.3
        assert res1["longitude"] == 76.65
        assert len(res1["daily"]) == 1
        assert res1["daily"][0]["date"] == today.isoformat()
        assert res1["daily"][0]["temperature_max_c"] == 31.5
        assert res1["daily"][0]["temperature_min_c"] == 21.0
        assert res1["daily"][0]["precipitation_probability_max"] == 25
        assert mock_get.call_count == 1

        # Second call with identical coords: must hit cache without any HTTP call
        res2 = get_weather_forecast(12.3, 76.65, today, today)
        assert res2["source"] == "Google Weather"
        assert res2["daily"] == res1["daily"]
        assert mock_get.call_count == 1  # No additional network call!


def test_cache_ttl_expiration(monkeypatch):
    """Cached responses are re-fetched after the 6-hour TTL expires."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_resp = _mock_google_response(200, [today])

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        get_weather_forecast(12.3, 76.65, today, today)
        assert mock_get.call_count == 1

        # Expire the cache entry
        coord_key = (round(12.3, 3), round(76.65, 3))
        assert coord_key in _WEATHER_CACHE
        _WEATHER_CACHE[coord_key]["expires_at"] = time.monotonic() - 1.0

        # Next call should re-fetch from upstream
        res2 = get_weather_forecast(12.3, 76.65, today, today)
        assert mock_get.call_count == 2
        assert res2["source"] == "Google Weather"


def test_missing_api_key_raises_runtime_error(monkeypatch):
    """Missing GOOGLE_WEATHER_KEY raises a RuntimeError without crashing."""
    monkeypatch.delenv("GOOGLE_WEATHER_KEY", raising=False)
    today = date.today()
    with pytest.raises(RuntimeError, match="key is not configured"):
        get_weather_forecast(12.3, 76.65, today, today)


def test_http_429_raises_runtime_error(monkeypatch):
    """Google Weather HTTP 429 raises a controlled RuntimeError."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()

    with patch("app.services.weather_service.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_client.get.return_value = mock_resp
        mock_cls.return_value = mock_client

        with pytest.raises(RuntimeError):
            get_weather_forecast(12.3, 76.65, today, today)


def test_network_failure_raises_runtime_error(monkeypatch):
    """Network failure raises a controlled RuntimeError."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    import httpx
    today = date.today()

    with patch("app.services.weather_service.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectTimeout("simulated")
        mock_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="temporarily unavailable"):
            get_weather_forecast(12.3, 76.65, today, today)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_response_schema(monkeypatch):
    """Response matches the NammaPrayana weather schema expected by frontend."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    required_day_keys = {"date", "weather_code", "temperature_max_c", "temperature_min_c", "precipitation_probability_max"}

    mock_resp = _mock_google_response(200, [today])
    with patch("httpx.Client.get", return_value=mock_resp):
        res = get_weather_forecast(12.3, 76.65, today, today)
        assert "latitude" in res and "longitude" in res
        assert res["source"] == "Google Weather"
        assert isinstance(res["daily"], list)
        assert len(res["daily"]) >= 1
        assert set(res["daily"][0].keys()) == required_day_keys


# ---------------------------------------------------------------------------
# Forecast horizon tests
# ---------------------------------------------------------------------------

def test_dates_within_window_no_notice(monkeypatch):
    """Dates within 10-day window → has_partial_forecast=False, no notice."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(4)]
    mock_resp = _mock_google_response(200, dates)

    with patch("httpx.Client.get", return_value=mock_resp):
        res = get_weather_forecast(12.3, 76.65, today, today + timedelta(days=3))
        assert res["has_partial_forecast"] is False
        assert res["forecast_notice"] is None
        assert len(res["daily"]) == 4


def test_dates_beyond_window_returns_notice(monkeypatch):
    """Dates beyond available forecast window → has_partial_forecast=True with polite notice."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    api_dates = [today + timedelta(days=i) for i in range(10)]
    mock_resp = _mock_google_response(200, api_dates)

    with patch("httpx.Client.get", return_value=mock_resp):
        res = get_weather_forecast(12.3, 76.65, today, today + timedelta(days=14))
        assert res["has_partial_forecast"] is True
        assert res["forecast_notice"] == FORECAST_NOTICE_TEXT
        assert len(res["daily"]) == 10  # Only real available days returned


# ---------------------------------------------------------------------------
# Deduplication test
# ---------------------------------------------------------------------------

def test_simultaneous_requests_deduplicated(monkeypatch):
    """Concurrent requests for the same coords are deduplicated upstream (1 HTTP call)."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_resp = _mock_google_response(200, [today])
    call_counter = 0

    def slow_mock_get(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        time.sleep(0.15)
        return mock_resp

    results = []

    def worker():
        results.append(get_weather_forecast(12.3, 76.65, today, today))

    with patch("httpx.Client.get", side_effect=slow_mock_get):
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(results) == 5
    for r in results:
        assert r["source"] == "Google Weather"
    assert call_counter == 1  # Only 1 upstream HTTP call despite 5 threads


# ---------------------------------------------------------------------------
# Condition mapping tests
# ---------------------------------------------------------------------------

def test_condition_mapping_clear():
    assert _map_google_condition_to_wmo("CLEAR") == 0
    assert _map_google_condition_to_wmo("SUNNY") == 0
    assert _map_google_condition_to_wmo("MOSTLY_CLEAR") == 1
    assert _map_google_condition_to_wmo("FAIR") == 1


def test_condition_mapping_cloudy():
    assert _map_google_condition_to_wmo("PARTLY_CLOUDY") == 2
    assert _map_google_condition_to_wmo("MOSTLY_CLOUDY") == 3
    assert _map_google_condition_to_wmo("OVERCAST") == 3


def test_condition_mapping_rain():
    assert _map_google_condition_to_wmo("LIGHT_RAIN") == 61
    assert _map_google_condition_to_wmo("MODERATE_RAIN") == 63
    assert _map_google_condition_to_wmo("HEAVY_RAIN") == 65


def test_condition_mapping_thunder():
    assert _map_google_condition_to_wmo("THUNDERSTORM") == 95
    assert _map_google_condition_to_wmo("HEAVY_THUNDERSTORM") == 96
    assert _map_google_condition_to_wmo("SEVERE_THUNDERSTORM") == 99


def test_condition_mapping_fog():
    assert _map_google_condition_to_wmo("FOG") == 45
    assert _map_google_condition_to_wmo("MIST") == 45
    assert _map_google_condition_to_wmo("HAZE") == 45


def test_condition_mapping_snow():
    assert _map_google_condition_to_wmo("LIGHT_SNOW") == 71
    assert _map_google_condition_to_wmo("HEAVY_SNOW") == 75


def test_condition_mapping_unknown_defaults():
    assert _map_google_condition_to_wmo(None, None) == 2
    assert _map_google_condition_to_wmo("XYZZY") == 2


def test_condition_mapping_description_fallback():
    assert _map_google_condition_to_wmo(None, "Heavy rain showers") == 61
    assert _map_google_condition_to_wmo(None, "Thunderstorm with lightning") == 95


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------

def test_past_date_raises_value_error():
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(ValueError, match="past dates"):
        get_weather_forecast(12.3, 76.65, yesterday, yesterday)


def test_end_before_start_raises_value_error():
    today = date.today()
    with pytest.raises(ValueError, match="End date"):
        get_weather_forecast(12.3, 76.65, today + timedelta(days=2), today)
