"""Daily weather forecasts with multi-provider resilience and in-memory caching."""

import logging
import os
import threading
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHERAPI_URL = "https://api.weatherapi.com/v1/forecast.json"

# Timeout for upstream weather provider calls
_TIMEOUT = httpx.Timeout(connect=8.0, read=12.0, write=5.0, pool=5.0)

# Force IPv4 transport for hosts where IPv6 to api.open-meteo.com is broken (e.g. Render)
try:
    _TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0")
except Exception:  # pragma: no cover
    _TRANSPORT = None

# Cache TTL: 6 hours
CACHE_TTL_SECONDS = 6 * 3600

# Cache storage: cache_key -> {"expires_at": float, "data": dict, "cached_at": float}
_FORECAST_CACHE: dict[tuple, dict] = {}
_CACHE_LOCK = threading.Lock()

# Deduplication of concurrent upstream fetches
_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT_EVENTS: dict[tuple, threading.Event] = {}

# Cooldown timestamp for Open-Meteo on HTTP 429
_OPEN_METEO_COOLDOWN_UNTIL: float = 0.0

# Mapping of WeatherAPI condition code to approximate WMO weather code
_WEATHERAPI_TO_WMO = {
    1000: 0,   # Sunny / Clear
    1003: 1,   # Partly cloudy
    1006: 2,   # Cloudy
    1009: 3,   # Overcast
    1030: 45,  # Mist
    1063: 61,  # Patchy rain possible
    1066: 71,  # Patchy snow possible
    1069: 51,  # Patchy sleet possible
    1072: 56,  # Patchy freezing drizzle
    1087: 95,  # Thundery outbreaks possible
    1114: 75,  # Blowing snow
    1117: 75,  # Blizzard
    1135: 45,  # Fog
    1147: 48,  # Freezing fog
    1150: 51,  # Patchy light drizzle
    1153: 51,  # Light drizzle
    1168: 56,  # Freezing drizzle
    1171: 57,  # Heavy freezing drizzle
    1180: 61,  # Patchy light rain
    1183: 61,  # Light rain
    1186: 63,  # Moderate rain at times
    1189: 63,  # Moderate rain
    1192: 65,  # Heavy rain at times
    1195: 65,  # Heavy rain
    1198: 66,  # Light freezing rain
    1201: 67,  # Moderate/heavy freezing rain
    1204: 57,  # Light sleet
    1207: 57,  # Moderate/heavy sleet
    1210: 71,  # Patchy light snow
    1213: 71,  # Light snow
    1216: 73,  # Patchy moderate snow
    1219: 73,  # Moderate snow
    1222: 75,  # Patchy heavy snow
    1225: 75,  # Heavy snow
    1237: 77,  # Ice pellets
    1240: 80,  # Light rain shower
    1243: 81,  # Moderate/heavy rain shower
    1246: 82,  # Torrential rain shower
    1249: 57,  # Light sleet showers
    1252: 57,  # Moderate/heavy sleet showers
    1255: 85,  # Light snow showers
    1258: 86,  # Moderate/heavy snow showers
    1261: 77,  # Light showers of ice pellets
    1264: 77,  # Moderate/heavy showers of ice pellets
    1273: 95,  # Patchy light rain with thunder
    1276: 96,  # Moderate/heavy rain with thunder
    1279: 95,  # Patchy light snow with thunder
    1282: 99,  # Moderate/heavy snow with thunder
}


def _map_weatherapi_code_to_wmo(code: int | None) -> int:
    """Map WeatherAPI condition code to approximate WMO code, defaulting to 2 (partly cloudy)."""
    if code is None:
        return 2
    try:
        return _WEATHERAPI_TO_WMO.get(int(code), 2)
    except (ValueError, TypeError):
        return 2


def clear_weather_cache():
    """Clear in-memory cache and reset rate-limiting state. Useful in unit tests."""
    global _OPEN_METEO_COOLDOWN_UNTIL
    with _CACHE_LOCK:
        _FORECAST_CACHE.clear()
    with _INFLIGHT_LOCK:
        _INFLIGHT_EVENTS.clear()
    _OPEN_METEO_COOLDOWN_UNTIL = 0.0


class OpenMeteoRateLimitError(Exception):
    """Raised when Open-Meteo returns HTTP 429."""

    def __init__(self, retry_after: float):
        super().__init__(f"Open-Meteo rate limit exceeded. Retry after {retry_after:.1f}s")
        self.retry_after = retry_after


def _parse_retry_after(header_val: str | None) -> float:
    """Parse HTTP Retry-After header as seconds or HTTP-date."""
    if not header_val:
        return 60.0
    try:
        val = float(header_val)
        return max(1.0, min(val, 3600.0))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(header_val)
        now_dt = datetime.now(timezone.utc)
        diff = (dt - now_dt).total_seconds()
        return max(1.0, min(diff, 3600.0))
    except Exception:
        return 60.0


def _fetch_open_meteo(
    latitude: float,
    longitude: float,
    effective_start: date,
    effective_end: date,
) -> dict:
    """Fetch forecast from primary provider (Open-Meteo)."""
    global _OPEN_METEO_COOLDOWN_UNTIL

    now = time.monotonic()
    if now < _OPEN_METEO_COOLDOWN_UNTIL:
        remaining = _OPEN_METEO_COOLDOWN_UNTIL - now
        logger.info(
            "[weather] Open-Meteo is in cooldown period (%.1fs remaining); bypassing to fallback",
            remaining,
        )
        raise OpenMeteoRateLimitError(remaining)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "timezone": "auto",
        "start_date": effective_start.isoformat(),
        "end_date": effective_end.isoformat(),
    }

    client_kwargs = {"timeout": _TIMEOUT}
    if _TRANSPORT is not None:
        client_kwargs["transport"] = _TRANSPORT

    try:
        with httpx.Client(**client_kwargs) as client:
            response = client.get(OPEN_METEO_URL, params=params)

            if response.status_code == 429:
                retry_after_hdr = response.headers.get("Retry-After")
                retry_after_sec = _parse_retry_after(retry_after_hdr)
                _OPEN_METEO_COOLDOWN_UNTIL = time.monotonic() + retry_after_sec
                logger.warning(
                    "[weather] Open-Meteo returned 429 Too Many Requests (Retry-After: %s). Cooldown set for %.1fs.",
                    retry_after_hdr,
                    retry_after_sec,
                )
                raise OpenMeteoRateLimitError(retry_after_sec)

            if response.status_code == 400:
                try:
                    err_json = response.json()
                    if err_json.get("reason"):
                        raise ValueError(err_json["reason"])
                except ValueError:
                    raise
                except Exception:
                    pass

            response.raise_for_status()
            payload = response.json()
    except (ValueError, OpenMeteoRateLimitError):
        raise
    except (httpx.HTTPError, Exception) as exc:
        logger.error("[weather] Open-Meteo request failed: %r", exc)
        raise RuntimeError("Weather provider is temporarily unavailable.") from exc

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []

    if not dates:
        raise RuntimeError("Weather provider returned no forecast data.")

    forecasts = []
    for index, forecast_date in enumerate(dates):
        forecasts.append({
            "date": forecast_date,
            "weather_code": (daily.get("weather_code") or [None] * len(dates))[index],
            "temperature_max_c": (
                daily.get("temperature_2m_max") or [None] * len(dates)
            )[index],
            "temperature_min_c": (
                daily.get("temperature_2m_min") or [None] * len(dates)
            )[index],
            "precipitation_probability_max": (
                daily.get("precipitation_probability_max") or [None] * len(dates)
            )[index],
        })

    return {
        "latitude": latitude,
        "longitude": longitude,
        "source": "Open-Meteo",
        "daily": forecasts,
    }


def _fetch_weatherapi(
    latitude: float,
    longitude: float,
    effective_start: date,
    effective_end: date,
) -> dict:
    """Fetch forecast from secondary fallback provider (WeatherAPI.com)."""
    api_key = os.getenv("WEATHERAPI_KEY", "").strip()
    if not api_key:
        logger.info("[weather] WEATHERAPI_KEY not configured; fallback skipped")
        raise RuntimeError("WeatherAPI fallback key is not configured.")

    today = date.today()
    max_weatherapi_date = today + timedelta(days=2)

    # WeatherAPI free tier advertises up to 3 days of forecast (today, today+1, today+2)
    if effective_start > max_weatherapi_date:
        logger.warning(
            "[weather] Requested start date %s is beyond WeatherAPI free plan horizon (%s)",
            effective_start.isoformat(),
            max_weatherapi_date.isoformat(),
        )
        raise RuntimeError(
            f"Requested forecast date ({effective_start.isoformat()}) exceeds WeatherAPI free plan horizon."
        )

    if effective_end > max_weatherapi_date:
        logger.warning(
            "[weather] Requested end date %s extends beyond WeatherAPI free plan horizon (%s)",
            effective_end.isoformat(),
            max_weatherapi_date.isoformat(),
        )
        raise RuntimeError(
            f"Requested forecast date range extends beyond WeatherAPI free plan horizon ({max_weatherapi_date.isoformat()})."
        )

    days_needed = (effective_end - today).days + 1
    days_param = max(1, min(days_needed, 3))

    params = {
        "key": api_key,
        "q": f"{latitude:.4f},{longitude:.4f}",
        "days": days_param,
        "aqi": "no",
        "alerts": "no",
    }

    client_kwargs = {"timeout": _TIMEOUT}
    if _TRANSPORT is not None:
        client_kwargs["transport"] = _TRANSPORT

    try:
        with httpx.Client(**client_kwargs) as client:
            response = client.get(WEATHERAPI_URL, params=params)
            if response.status_code == 400:
                logger.warning("[weather] WeatherAPI returned 400")
                raise RuntimeError("WeatherAPI rejected query parameters.")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, Exception) as exc:
        # Never log API key or query parameters that contain secret tokens
        logger.error("[weather] WeatherAPI request failed: %s", type(exc).__name__)
        raise RuntimeError("WeatherAPI provider failed.") from exc

    forecast_days = (payload.get("forecast") or {}).get("forecastday") or []
    if not forecast_days:
        raise RuntimeError("WeatherAPI returned no forecast day data.")

    days_by_date = {item.get("date"): item for item in forecast_days if item.get("date")}

    curr = effective_start
    forecasts = []
    while curr <= effective_end:
        d_str = curr.isoformat()
        if d_str not in days_by_date:
            raise RuntimeError(f"WeatherAPI missing forecast for date: {d_str}")

        fday = days_by_date[d_str]
        day_data = fday.get("day") or {}
        cond = day_data.get("condition") or {}
        raw_code = cond.get("code")
        w_code = _WEATHERAPI_TO_WMO.get(int(raw_code), 2) if raw_code is not None else 2

        pop = day_data.get("daily_chance_of_rain")
        try:
            pop_int = int(round(float(pop))) if pop is not None else None
        except (ValueError, TypeError):
            pop_int = None

        forecasts.append({
            "date": d_str,
            "weather_code": w_code,
            "temperature_max_c": day_data.get("maxtemp_c"),
            "temperature_min_c": day_data.get("mintemp_c"),
            "precipitation_probability_max": pop_int,
        })
        curr += timedelta(days=1)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "source": "WeatherAPI",
        "daily": forecasts,
    }


def get_weather_forecast(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict:
    """Return daily forecast data with 6-hour caching and WeatherAPI fallback."""

    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")

    today = date.today()
    max_forecast_date = today + timedelta(days=14)

    if end_date < today:
        raise ValueError("Weather forecasts are not available for past dates.")

    effective_start = max(start_date, today)
    if effective_start > max_forecast_date:
        raise ValueError(
            f"Weather forecasts are only available up to {max_forecast_date.isoformat()} (15-day forecast horizon). "
            f"Requested start date {start_date.isoformat()} is beyond this window."
        )

    effective_end = min(end_date, max_forecast_date)

    cache_key = (
        round(latitude, 3),
        round(longitude, 3),
        effective_start.isoformat(),
        effective_end.isoformat(),
    )

    # 1. Check in-process cache (fresh entries valid for 6 hours)
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _FORECAST_CACHE.get(cache_key)
        if entry and now < entry["expires_at"]:
            return entry["data"]

    # 2. Avoid duplicate simultaneous upstream requests for the same cache key
    my_event = None
    with _INFLIGHT_LOCK:
        if cache_key in _INFLIGHT_EVENTS:
            waiting_event = _INFLIGHT_EVENTS[cache_key]
        else:
            waiting_event = None
            my_event = threading.Event()
            _INFLIGHT_EVENTS[cache_key] = my_event

    if waiting_event is not None:
        # Another request for this identical key is already in flight; wait for it
        waiting_event.wait(timeout=15.0)
        with _CACHE_LOCK:
            entry = _FORECAST_CACHE.get(cache_key)
            if entry and time.monotonic() < entry["expires_at"]:
                return entry["data"]
            if entry and "data" in entry:
                stale_copy = dict(entry["data"])
                orig_source = stale_copy.get("source", "Weather")
                stale_copy["source"] = f"{orig_source} (stale cache)"
                stale_copy["is_stale"] = True
                return stale_copy
        # If still no cached data after wait, leader may have succeeded right as event set
        with _CACHE_LOCK:
            if cache_key in _FORECAST_CACHE:
                return _FORECAST_CACHE[cache_key]["data"]

    # 3. We are the leader thread: fetch upstream with fallback
    last_error: Exception | None = None
    result: dict | None = None

    try:
        # Try Open-Meteo first
        try:
            result = _fetch_open_meteo(latitude, longitude, effective_start, effective_end)
        except OpenMeteoRateLimitError as exc:
            last_error = exc
            logger.warning("[weather] Open-Meteo 429/cooldown triggered fallback: %s", exc)
        except (RuntimeError, httpx.HTTPError) as exc:
            last_error = exc
            logger.warning("[weather] Open-Meteo failed, trying fallback: %s", exc)

        # If Open-Meteo failed, try WeatherAPI fallback
        if result is None:
            try:
                result = _fetch_weatherapi(latitude, longitude, effective_start, effective_end)
            except Exception as fb_exc:
                logger.error("[weather] WeatherAPI fallback also failed: %s", fb_exc)
                if last_error is None:
                    last_error = fb_exc

        # If a provider succeeded, cache the result
        if result is not None:
            with _CACHE_LOCK:
                _FORECAST_CACHE[cache_key] = {
                    "expires_at": time.monotonic() + CACHE_TTL_SECONDS,
                    "data": result,
                    "cached_at": time.monotonic(),
                }
            return result

        # Both providers failed — use a clearly labelled stale cached forecast if one exists
        with _CACHE_LOCK:
            stale_entry = _FORECAST_CACHE.get(cache_key)
            if stale_entry and "data" in stale_entry:
                logger.warning(
                    "[weather] Providers unavailable; returning stale cached forecast for %s",
                    cache_key,
                )
                stale_copy = dict(stale_entry["data"])
                orig_source = stale_copy.get("source", "Weather")
                stale_copy["source"] = f"{orig_source} (stale cache)"
                stale_copy["is_stale"] = True
                return stale_copy

        # Controlled service-unavailable response when no stale cache exists; never fabricate data
        raise RuntimeError("Weather forecast is temporarily unavailable from all providers.") from last_error

    finally:
        if my_event is not None:
            my_event.set()
            with _INFLIGHT_LOCK:
                _INFLIGHT_EVENTS.pop(cache_key, None)
