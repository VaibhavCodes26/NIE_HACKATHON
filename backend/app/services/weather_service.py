"""Daily weather forecasts powered exclusively by Google Weather API.

Endpoints and data conform strictly to the official Google Weather API:
https://weather.googleapis.com/v1/forecast/days:lookup
"""

import json
import logging
import os
import random
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

GOOGLE_WEATHER_URL = "https://weather.googleapis.com/v1/forecast/days:lookup"

# Client timeouts for Google Weather API calls: sensible connect, read, write, pool limits
_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

# Retry configuration for transient errors
MAX_RETRIES = 2  # Total 3 attempts
BASE_BACKOFF_SECS = 0.5
MAX_BACKOFF_SECS = 5.0

TRANSIENT_EXCEPTIONS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    httpx.NetworkError,
)

# IPv4 transport for cloud hosts where IPv6 handshake stalls
try:
    _TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0", retries=0)
except Exception:  # pragma: no cover
    _TRANSPORT = None

# Persistent HTTP Client with connection pooling and thread safety
_WEATHER_CLIENT: httpx.Client | None = None
_CLIENT_LOCK = threading.Lock()

# Cache TTL: 6 hours for fresh cache, 24 hours for stale fallback during upstream outages
CACHE_TTL_SECONDS = 6 * 3600
STALE_FALLBACK_TTL_SECONDS = 24 * 3600

# L1 In-memory cache storage: (round(lat, 3), round(lon, 3)) -> {"expires_at": float, "data": dict, "cached_at": float}
_WEATHER_CACHE: dict[tuple, dict] = {}
_CACHE_LOCK = threading.Lock()

# Deduplication for simultaneous in-flight requests
_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT_EVENTS: dict[tuple, threading.Event] = {}

FORECAST_NOTICE_TEXT = (
    "Weather forecasts are currently available for up to 10 days from today. "
    "Sorry for the inconvenience! Weather updates for your remaining trip dates aren't available yet."
)

# Comprehensive mapping of Google Weather API condition types/descriptions to WMO weather codes
_GOOGLE_CONDITION_TO_WMO = {
    # Clear / Sunny
    "CLEAR": 0,
    "SUNNY": 0,
    "CLEAR_DAY": 0,
    "CLEAR_NIGHT": 0,
    "MOSTLY_CLEAR": 1,
    "MOSTLY_SUNNY": 1,
    "FAIR": 1,
    # Cloudy
    "PARTLY_CLOUDY": 2,
    "PARTLY_SUNNY": 2,
    "MOSTLY_CLOUDY": 3,
    "CLOUDY": 3,
    "OVERCAST": 3,
    # Fog / Mist / Haze
    "FOG": 45,
    "FOGGY": 45,
    "MIST": 45,
    "HAZE": 45,
    "SMOKE": 45,
    "DUST": 45,
    "SAND": 45,
    # Drizzle
    "DRIZZLE": 51,
    "LIGHT_DRIZZLE": 51,
    "PATCHY_LIGHT_DRIZZLE": 51,
    "FREEZING_DRIZZLE": 56,
    "HEAVY_FREEZING_DRIZZLE": 57,
    # Rain
    "LIGHT_RAIN": 61,
    "PATCHY_LIGHT_RAIN": 61,
    "RAIN": 63,
    "MODERATE_RAIN": 63,
    "HEAVY_RAIN": 65,
    "TORRENTIAL_RAIN": 65,
    "FREEZING_RAIN": 66,
    "LIGHT_FREEZING_RAIN": 66,
    "HEAVY_FREEZING_RAIN": 67,
    # Showers
    "LIGHT_RAIN_SHOWERS": 80,
    "CHANCE_OF_SHOWERS": 80,
    "SCATTERED_SHOWERS": 80,
    "RAIN_SHOWERS": 81,
    "SHOWERS": 81,
    "HEAVY_RAIN_SHOWERS": 82,
    "VIOLENT_RAIN_SHOWERS": 82,
    # Thunderstorm
    "THUNDERSTORM": 95,
    "LIGHT_THUNDERSTORM_RAIN": 95,
    "SCATTERED_THUNDERSTORMS": 95,
    "THUNDERSHOWER": 95,
    "HEAVY_THUNDERSTORM": 96,
    "THUNDERSTORM_WITH_HAIL": 96,
    "SEVERE_THUNDERSTORM": 99,
    # Snow
    "LIGHT_SNOW": 71,
    "SNOW": 73,
    "HEAVY_SNOW": 75,
    "SNOW_SHOWERS": 85,
    "BLIZZARD": 75,
    "SLEET": 57,
    "ICE_PELLETS": 77,
    "HAIL": 96,
    # Wind
    "WINDY": 1,
    "BREEZY": 1,
    "WIND_AND_RAIN": 63,
}


def _get_cache_db_path() -> str:
    """Return absolute path to persistent SQLite weather cache."""
    env_path = os.getenv("WEATHER_CACHE_PATH", "").strip()
    if env_path:
        return env_path
    base_dir = Path(__file__).resolve().parent.parent
    return str(base_dir / "weather_cache.sqlite")


def _init_sqlite_cache():
    """Ensure persistent SQLite cache table and index exist."""
    db_path = _get_cache_db_path()
    try:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS weather_cache (
                    coord_key TEXT PRIMARY KEY,
                    latitude REAL,
                    longitude REAL,
                    data_json TEXT,
                    cached_at REAL,
                    expires_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_weather_cache_expires
                ON weather_cache (expires_at)
                """
            )
    except Exception as exc:
        logger.warning("[weather] Could not initialize SQLite cache at %s: %s", db_path, exc)


# Initialize SQLite table on module load
_init_sqlite_cache()


def get_weather_http_client() -> httpx.Client:
    """Return or create a thread-safe persistent httpx.Client with connection pooling."""
    global _WEATHER_CLIENT
    with _CLIENT_LOCK:
        if _WEATHER_CLIENT is None or _WEATHER_CLIENT.is_closed:
            limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0,
            )
            client_kwargs = {
                "timeout": _TIMEOUT,
                "limits": limits,
            }
            if _TRANSPORT is not None:
                client_kwargs["transport"] = _TRANSPORT

            _WEATHER_CLIENT = httpx.Client(**client_kwargs)
        return _WEATHER_CLIENT


def close_weather_http_client():
    """Cleanly close the persistent HTTP client and underlying connection pool."""
    global _WEATHER_CLIENT
    with _CLIENT_LOCK:
        if _WEATHER_CLIENT is not None and not _WEATHER_CLIENT.is_closed:
            try:
                _WEATHER_CLIENT.close()
            except Exception:
                pass
            _WEATHER_CLIENT = None


def _get_from_cache(coord_key: tuple, allow_stale: bool = False) -> tuple[dict | None, float | None, bool]:
    """Retrieve forecast from in-memory L1 or persistent SQLite L2 cache.

    Returns (data, cached_at_timestamp, is_stale).
    """
    now_m = time.monotonic()
    now_t = time.time()

    # 1. Check L1 Memory cache
    with _CACHE_LOCK:
        entry = _WEATHER_CACHE.get(coord_key)
        if entry:
            if now_m < entry["expires_at"]:
                return entry["data"], entry.get("cached_at", now_t), False
            if allow_stale and now_t < (entry.get("cached_at", 0) + STALE_FALLBACK_TTL_SECONDS):
                return entry["data"], entry.get("cached_at", now_t), True
            if not allow_stale:
                return None, None, False

    # 2. Check L2 SQLite cache
    db_path = _get_cache_db_path()
    key_str = f"{coord_key[0]:.3f},{coord_key[1]:.3f}"
    try:
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_json, cached_at, expires_at FROM weather_cache WHERE coord_key = ?",
                (key_str,),
            )
            row = cursor.fetchone()
            if row:
                data_json, cached_at_t, expires_at_t = row
                data = json.loads(data_json)
                if now_t < expires_at_t:
                    remaining = max(0.0, expires_at_t - now_t)
                    with _CACHE_LOCK:
                        _WEATHER_CACHE[coord_key] = {
                            "expires_at": now_m + remaining,
                            "data": data,
                            "cached_at": cached_at_t,
                        }
                    return data, cached_at_t, False
                if allow_stale and now_t < (cached_at_t + STALE_FALLBACK_TTL_SECONDS):
                    return data, cached_at_t, True
    except Exception as exc:
        logger.warning("[weather] SQLite cache read error: %s", exc)

    return None, None, False


def _save_to_cache(coord_key: tuple, latitude: float, longitude: float, days_by_date: dict):
    """Save forecast into both in-memory L1 and persistent SQLite L2 cache."""
    now_m = time.monotonic()
    now_t = time.time()
    expires_at_m = now_m + CACHE_TTL_SECONDS
    expires_at_t = now_t + CACHE_TTL_SECONDS

    # 1. Update L1 Memory cache
    with _CACHE_LOCK:
        _WEATHER_CACHE[coord_key] = {
            "expires_at": expires_at_m,
            "data": days_by_date,
            "cached_at": now_t,
        }

    # 2. Update L2 SQLite cache
    db_path = _get_cache_db_path()
    key_str = f"{coord_key[0]:.3f},{coord_key[1]:.3f}"
    try:
        data_json = json.dumps(days_by_date)
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO weather_cache
                (coord_key, latitude, longitude, data_json, cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key_str, latitude, longitude, data_json, now_t, expires_at_t),
            )
    except Exception as exc:
        logger.warning("[weather] SQLite cache write error: %s", exc)


def clear_weather_cache():
    """Clear in-memory cache, persistent SQLite cache, inflight events, and HTTP client (used in unit tests)."""
    with _CACHE_LOCK:
        _WEATHER_CACHE.clear()
    with _INFLIGHT_LOCK:
        _INFLIGHT_EVENTS.clear()
    db_path = _get_cache_db_path()
    try:
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.execute("DELETE FROM weather_cache")
    except Exception:
        pass
    close_weather_http_client()


def _map_google_condition_to_wmo(cond_type: str | None, description: str | None = None) -> int:
    """Map Google Weather API condition type or description to approximate WMO code."""
    if cond_type:
        normalized = str(cond_type).strip().upper().replace(" ", "_")
        if normalized in _GOOGLE_CONDITION_TO_WMO:
            return _GOOGLE_CONDITION_TO_WMO[normalized]

        # Substring heuristics for compound enum names
        if "THUNDER" in normalized:
            return 96 if "HAIL" in normalized else 95
        if "HEAVY_RAIN" in normalized or "TORRENTIAL" in normalized:
            return 65
        if "RAIN" in normalized or "SHOWER" in normalized:
            return 61
        if "DRIZZLE" in normalized:
            return 51
        if "SNOW" in normalized:
            return 71
        if any(f in normalized for f in ("FOG", "MIST", "HAZE")):
            return 45
        if "CLEAR" in normalized or "SUN" in normalized:
            return 0
        if "CLOUD" in normalized or "OVERCAST" in normalized:
            return 2

    if description:
        desc_upper = str(description).strip().upper()
        if "THUNDER" in desc_upper:
            return 95
        if "RAIN" in desc_upper or "SHOWER" in desc_upper:
            return 61
        if "DRIZZLE" in desc_upper:
            return 51
        if "FOG" in desc_upper or "MIST" in desc_upper:
            return 45
        if "CLEAR" in desc_upper or "SUN" in desc_upper:
            return 0
        if "CLOUD" in desc_upper:
            return 2

    return 2  # Default to 2 (partly cloudy)


def _fetch_google_weather(latitude: float, longitude: float) -> dict[str, dict]:
    """Call Google Weather API days:lookup endpoint with retries and parse the up-to-10-day forecast.

    Implements a bounded retry policy with exponential backoff and jitter for transient network failures,
    timeouts, HTTP 429, and retryable upstream 5xx errors.
    Returns dict mapping date_string (YYYY-MM-DD) -> daily forecast object.
    """
    api_key = os.getenv("GOOGLE_WEATHER_KEY", "").strip()
    if not api_key:
        logger.error("[weather] GOOGLE_WEATHER_KEY is not configured in backend environment.")
        raise RuntimeError("Google Weather API key is not configured.")

    params = {
        "key": api_key,
        "location.latitude": f"{latitude:.4f}",
        "location.longitude": f"{longitude:.4f}",
        "days": 10,
        "pageSize": 10,
    }

    client = get_weather_http_client()
    payload = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.get(GOOGLE_WEATHER_URL, params=params)

            # Non-retryable client errors (Bad Request, Unauthorized, Forbidden, Not Found)
            if response.status_code in (400, 401, 403, 404):
                logger.error("[weather] Google Weather API client error (%s): %s", response.status_code, response.text[:200])
                raise RuntimeError("Google Weather API request or authentication failed.")

            # Rate limit (429)
            if response.status_code == 429:
                if attempt < MAX_RETRIES:
                    retry_after_hdr = response.headers.get("Retry-After")
                    delay = None
                    if retry_after_hdr:
                        try:
                            delay = min(float(retry_after_hdr), MAX_BACKOFF_SECS)
                        except (ValueError, TypeError):
                            delay = None
                    if delay is None:
                        delay = min(BASE_BACKOFF_SECS * (2 ** attempt) + random.uniform(0.05, 0.25), MAX_BACKOFF_SECS)
                    logger.warning(
                        "[weather] Google Weather API rate limit (429) on attempt %d/%d; retrying in %.2fs",
                        attempt + 1,
                        MAX_RETRIES + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error("[weather] Google Weather API rate limit (429) exhausted retries.")
                    raise RuntimeError("Weather provider rate limit reached. Please try again shortly.")

            # Upstream 5xx server errors
            if response.status_code in (500, 502, 503, 504):
                if attempt < MAX_RETRIES:
                    delay = min(BASE_BACKOFF_SECS * (2 ** attempt) + random.uniform(0.05, 0.25), MAX_BACKOFF_SECS)
                    logger.warning(
                        "[weather] Google Weather API server error (%s) on attempt %d/%d; retrying in %.2fs",
                        response.status_code,
                        attempt + 1,
                        MAX_RETRIES + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                else:
                    response.raise_for_status()

            response.raise_for_status()
            payload = response.json()
            break

        except TRANSIENT_EXCEPTIONS as exc:
            if attempt < MAX_RETRIES:
                delay = min(BASE_BACKOFF_SECS * (2 ** attempt) + random.uniform(0.05, 0.25), MAX_BACKOFF_SECS)
                logger.warning(
                    "[weather] Transient %s on attempt %d/%d; retrying in %.2fs",
                    type(exc).__name__,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    delay,
                )
                time.sleep(delay)
                continue
            else:
                logger.error(
                    "[weather] Google Weather request failed after %d attempts: %s",
                    attempt + 1,
                    type(exc).__name__,
                )
                raise RuntimeError("Weather provider is temporarily unavailable.") from exc
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("[weather] Google Weather request unexpected failure: %s", type(exc).__name__)
            raise RuntimeError("Weather provider is temporarily unavailable.") from exc

    if payload is None:
        raise RuntimeError("Weather provider is temporarily unavailable.")

    raw_days = payload.get("forecastDays") or []
    days_by_date: dict[str, dict] = {}

    for item in raw_days:
        # Date string formatting
        date_str = None
        disp = item.get("displayDate")
        if isinstance(disp, dict) and "year" in disp and "month" in disp and "day" in disp:
            date_str = f"{int(disp['year']):04d}-{int(disp['month']):02d}-{int(disp['day']):02d}"
        elif item.get("interval", {}).get("startTime"):
            date_str = str(item["interval"]["startTime"])[:10]
        elif item.get("date"):
            date_str = str(item["date"])[:10]

        if not date_str:
            continue

        # Max temperature
        max_c = None
        if item.get("maxTemperature") and item["maxTemperature"].get("degrees") is not None:
            max_c = item["maxTemperature"]["degrees"]
        elif item.get("daytimeForecast", {}).get("maxTemperature", {}).get("degrees") is not None:
            max_c = item["daytimeForecast"]["maxTemperature"]["degrees"]
        elif item.get("daytimeForecast", {}).get("temperature", {}).get("degrees") is not None:
            max_c = item["daytimeForecast"]["temperature"]["degrees"]

        if max_c is not None:
            try:
                max_c = round(float(max_c), 1)
            except (ValueError, TypeError):
                max_c = None

        # Min temperature
        min_c = None
        if item.get("minTemperature") and item["minTemperature"].get("degrees") is not None:
            min_c = item["minTemperature"]["degrees"]
        elif item.get("nighttimeForecast", {}).get("minTemperature", {}).get("degrees") is not None:
            min_c = item["nighttimeForecast"]["minTemperature"]["degrees"]
        elif item.get("nighttimeForecast", {}).get("temperature", {}).get("degrees") is not None:
            min_c = item["nighttimeForecast"]["temperature"]["degrees"]

        if min_c is not None:
            try:
                min_c = round(float(min_c), 1)
            except (ValueError, TypeError):
                min_c = None

        # Precipitation probability
        daytime = item.get("daytimeForecast") or {}
        precip = daytime.get("precipitation") or item.get("precipitation") or {}
        prob_val = None
        if isinstance(precip.get("probability"), dict):
            prob_val = precip["probability"].get("percent")
        elif precip.get("probability") is not None:
            prob_val = precip.get("probability")
        elif item.get("precipitationProbability") is not None:
            prob_val = item.get("precipitationProbability")

        if prob_val is not None:
            try:
                prob_int = int(round(float(prob_val)))
            except (ValueError, TypeError):
                prob_int = None
        else:
            prob_int = None

        # Weather condition
        cond_obj = daytime.get("weatherCondition") or item.get("weatherCondition") or {}
        cond_type = cond_obj.get("type") or cond_obj.get("icon")
        cond_desc = (
            cond_obj.get("description", {}).get("text")
            if isinstance(cond_obj.get("description"), dict)
            else cond_obj.get("description")
        )
        w_code = _map_google_condition_to_wmo(cond_type, cond_desc)

        days_by_date[date_str] = {
            "date": date_str,
            "weather_code": w_code,
            "temperature_max_c": max_c,
            "temperature_min_c": min_c,
            "precipitation_probability_max": prob_int,
        }

    return days_by_date


def get_weather_forecast(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict:
    """Return daily forecast data from Google Weather API with caching and fallback.

    Respects the 10-day forecast horizon. If dates are beyond the horizon,
    returns real data for available dates and a polite inline forecast notice
    without inventing data or throwing unhandled errors.

    If Google Weather encounters a temporary upstream failure, serves valid cached
    forecast data if available within the fallback window, clearly labelled as cached.
    """
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")

    today = date.today()

    if end_date < today:
        raise ValueError("Weather forecasts are not available for past dates.")

    effective_start = max(start_date, today)
    effective_end = end_date

    coord_key = (round(latitude, 3), round(longitude, 3))

    # 1. Check in-process / persistent SQLite cache (fresh within 6 hours)
    cached_days, cached_at_ts, _ = _get_from_cache(coord_key, allow_stale=False)
    is_cached = cached_days is not None
    is_fallback = False

    # 2. In-flight request deduplication and fetch
    if cached_days is None:
        my_event = None
        with _INFLIGHT_LOCK:
            if coord_key in _INFLIGHT_EVENTS:
                waiting_event = _INFLIGHT_EVENTS[coord_key]
            else:
                waiting_event = None
                my_event = threading.Event()
                _INFLIGHT_EVENTS[coord_key] = my_event

        if waiting_event is not None:
            waiting_event.wait(timeout=15.0)
            cached_days, cached_at_ts, _ = _get_from_cache(coord_key, allow_stale=False)
            if cached_days is not None:
                is_cached = True

        if cached_days is None:
            try:
                days_by_date = _fetch_google_weather(latitude, longitude)
                _save_to_cache(coord_key, latitude, longitude, days_by_date)
                cached_days = days_by_date
                cached_at_ts = time.time()
                is_cached = False
                is_fallback = False
            except RuntimeError as exc:
                # Upstream outage or failure: fallback to stale cached forecast (within 24 hours) if available
                stale_days, stale_at, _ = _get_from_cache(coord_key, allow_stale=True)
                if stale_days is not None:
                    logger.warning(
                        "[weather] Using cached forecast fallback for (%s, %s) following upstream error: %s",
                        latitude,
                        longitude,
                        exc,
                    )
                    cached_days = stale_days
                    cached_at_ts = stale_at
                    is_cached = True
                    is_fallback = True
                else:
                    raise
            finally:
                if my_event is not None:
                    my_event.set()
                    with _INFLIGHT_LOCK:
                        _INFLIGHT_EVENTS.pop(coord_key, None)

    # 3. Match requested trip dates against available Google forecast dates
    max_avail_date = max(cached_days.keys()) if cached_days else None

    # Check if any requested date falls outside the available 10-day forecast window
    has_partial = False
    if not cached_days:
        has_partial = True
    elif max_avail_date and (
        effective_end.isoformat() > max_avail_date or effective_start.isoformat() > max_avail_date
    ):
        has_partial = True

    # Build real forecast list for dates that actually exist
    forecasts = []
    curr = effective_start
    while curr <= effective_end:
        d_str = curr.isoformat()
        if d_str in cached_days:
            forecasts.append(cached_days[d_str])
        curr += timedelta(days=1)

    if is_fallback:
        fallback_notice = "Live weather is temporarily unavailable. Showing recently cached forecast."
        forecast_notice = f"{fallback_notice} {FORECAST_NOTICE_TEXT}" if has_partial else fallback_notice
    else:
        forecast_notice = FORECAST_NOTICE_TEXT if has_partial else None

    cached_at_iso = (
        datetime.fromtimestamp(cached_at_ts, tz=timezone.utc).isoformat()
        if cached_at_ts
        else None
    )

    return {
        "latitude": latitude,
        "longitude": longitude,
        "source": "Google Weather",
        "daily": forecasts,
        "has_partial_forecast": has_partial,
        "forecast_notice": forecast_notice,
        "is_cached": is_cached,
        "is_fallback": is_fallback,
        "cached_at": cached_at_iso,
    }
