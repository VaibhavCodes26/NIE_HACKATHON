"""Unit tests for Google Weather API service: caching, deduplication, condition mapping, and horizon handling.

All tests mock Google Weather API HTTP calls using unittest.mock to avoid consuming real API quota.
"""

import httpx
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


# ---------------------------------------------------------------------------
# Section 8 Comprehensive Automated Test Suite
# ---------------------------------------------------------------------------

from starlette.testclient import TestClient
from app.main import app

api_client = TestClient(app)


def _make_mock_client(get_side_effect=None, get_return_value=None):
    mock_client = MagicMock()
    mock_client.is_closed = False
    if get_side_effect is not None:
        mock_client.get.side_effect = get_side_effect
    elif get_return_value is not None:
        mock_client.get.return_value = get_return_value
    return mock_client


def test_transient_read_error_followed_by_success(monkeypatch):
    """Case 2: A transient ReadError on attempt 1 followed by success on attempt 2."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_success = _mock_google_response(200, [today])
    mock_client = _make_mock_client(get_side_effect=[httpx.ReadError("connection reset"), mock_success])

    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            res = get_weather_forecast(12.3, 76.65, today, today)
            assert res["source"] == "Google Weather"
            assert len(res["daily"]) == 1
            assert mock_client.get.call_count == 2


def test_connection_and_read_timeouts_with_success(monkeypatch):
    """Case 3: Connection timeout on attempt 1, read timeout on attempt 2, success on attempt 3."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_success = _mock_google_response(200, [today])
    mock_client = _make_mock_client(get_side_effect=[
        httpx.ConnectTimeout("connect timed out"),
        httpx.ReadTimeout("read timed out"),
        mock_success,
    ])

    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            res = get_weather_forecast(12.3, 76.65, today, today)
            assert res["source"] == "Google Weather"
            assert mock_client.get.call_count == 3


def test_exhausted_retries_on_read_error(monkeypatch):
    """Case 4: Transient ReadError persists across all retries, then raises RuntimeError."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_client = _make_mock_client(get_side_effect=httpx.ReadError("connection dropped"))

    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="temporarily unavailable"):
                get_weather_forecast(12.3, 76.65, today, today)
            assert mock_client.get.call_count == 3  # Initial + 2 retries


def test_retry_on_429_with_retry_after(monkeypatch):
    """Case 5a: HTTP 429 with Retry-After header retries and succeeds."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "1"}
    mock_success = _mock_google_response(200, [today])
    mock_client = _make_mock_client(get_side_effect=[mock_429, mock_success])

    with patch("time.sleep") as mock_sleep:
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            res = get_weather_forecast(12.3, 76.65, today, today)
            assert res["source"] == "Google Weather"
            assert mock_client.get.call_count == 2
            mock_sleep.assert_called_with(1.0)


def test_retry_on_503_upstream_error(monkeypatch):
    """Case 5b: Retryable upstream 503 response retries and succeeds."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_success = _mock_google_response(200, [today])
    mock_client = _make_mock_client(get_side_effect=[mock_503, mock_success])

    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            res = get_weather_forecast(12.3, 76.65, today, today)
            assert res["source"] == "Google Weather"
            assert mock_client.get.call_count == 2


def test_non_retryable_client_errors_fail_fast(monkeypatch):
    """Case 6: HTTP 400, 401, 403 fail immediately without retrying."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()

    for status in (400, 401, 403):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.text = f"Simulated {status} client error"
        mock_client = _make_mock_client(get_return_value=mock_resp)

        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="authentication failed"):
                get_weather_forecast(12.3, 76.65, today, today)
            assert mock_client.get.call_count == 1  # No retry!


def test_cache_fallback_after_upstream_failure(monkeypatch):
    """Case 7: Valid stale cache is served as fallback when upstream fails."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_success = _mock_google_response(200, [today])
    mock_client = _make_mock_client(get_return_value=mock_success)

    # 1. Warm cache
    with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
        res1 = get_weather_forecast(12.3, 76.65, today, today)
        assert res1["is_cached"] is False
        assert res1["is_fallback"] is False

    # 2. Expire cache past fresh TTL (6h), but within 24h fallback window
    coord_key = (round(12.3, 3), round(76.65, 3))
    assert coord_key in _WEATHER_CACHE
    _WEATHER_CACHE[coord_key]["expires_at"] = time.monotonic() - 10.0

    # 3. Upstream fails with ReadError -> fallback cached data is returned
    mock_fail_client = _make_mock_client(get_side_effect=httpx.ReadError("connection dropped"))
    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_fail_client):
            res2 = get_weather_forecast(12.3, 76.65, today, today)
            assert res2["is_cached"] is True
            assert res2["is_fallback"] is True
            assert "Live weather is temporarily unavailable" in res2["forecast_notice"]
            assert len(res2["daily"]) == 1


def test_no_cache_failure_handling(monkeypatch):
    """Case 8: When no cached data exists and upstream fails, raises RuntimeError."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_client = _make_mock_client(get_side_effect=httpx.ReadError("network down"))

    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="temporarily unavailable"):
                get_weather_forecast(12.3, 76.65, today, today)


def test_partial_success_across_destinations(monkeypatch):
    """Case 9: Coorg succeeds while Shivamogga fails; Coorg remains 200, Shivamogga returns 502."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    coorg_resp = _mock_google_response(200, [today])

    def mock_get_route(url, params=None, **kwargs):
        lat = (params or {}).get("location.latitude")
        if lat == "12.4244":  # Coorg
            return coorg_resp
        # Shivamogga: 13.9299 -> fails
        raise httpx.ReadError("network failure for shivamogga")

    mock_client = _make_mock_client(get_side_effect=mock_get_route)

    with patch("time.sleep"):
        with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
            # 1. Query Coorg -> 200 OK
            r_coorg = api_client.get("/api/weather/forecast?destination=coorg")
            assert r_coorg.status_code == 200
            data_coorg = r_coorg.json()
            assert data_coorg["source"] == "Google Weather"
            assert len(data_coorg["daily"]) >= 1

            # 2. Query Shivamogga -> 502 Bad Gateway
            r_shivamogga = api_client.get("/api/weather/forecast?destination=shivamogga")
            assert r_shivamogga.status_code == 502
            assert r_shivamogga.json()["detail"] == "Weather forecast is temporarily unavailable."

            # 3. Coorg's forecast was not discarded and can still be fetched
            r_coorg_again = api_client.get("/api/weather/forecast?destination=coorg")
            assert r_coorg_again.status_code == 200
            assert r_coorg_again.json()["daily"] == data_coorg["daily"]


def test_dates_beyond_horizon_honestly_empty(monkeypatch):
    """Case 10: Dates completely beyond Google forecast horizon return empty daily and polite notice."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    # Mock Google returning 10 days from today
    api_dates = [today + timedelta(days=i) for i in range(10)]
    mock_resp = _mock_google_response(200, api_dates)
    mock_client = _make_mock_client(get_return_value=mock_resp)

    with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
        # Request dates from day 20 to day 22
        res = get_weather_forecast(12.3, 76.65, today + timedelta(days=20), today + timedelta(days=22))
        assert res["daily"] == []  # Never invent data
        assert res["has_partial_forecast"] is True
        assert res["forecast_notice"] == FORECAST_NOTICE_TEXT


def test_weather_endpoint_schema_contract(monkeypatch):
    """Case 11 & 12: Verify all expected schema fields for frontend consumption."""
    monkeypatch.setenv("GOOGLE_WEATHER_KEY", "test-api-key")
    today = date.today()
    mock_resp = _mock_google_response(200, [today])
    mock_client = _make_mock_client(get_return_value=mock_resp)

    with patch("app.services.weather_service.get_weather_http_client", return_value=mock_client):
        resp = api_client.get(f"/api/weather/forecast?destination=mysuru&start_date={today}&end_date={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert "latitude" in data
        assert "longitude" in data
        assert "source" in data
        assert "daily" in data
        assert "has_partial_forecast" in data
        assert "forecast_notice" in data
        assert "is_cached" in data
        assert "is_fallback" in data
        assert "cached_at" in data
