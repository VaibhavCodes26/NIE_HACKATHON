"""Daily weather forecasts powered exclusively by Google Weather API.

Endpoints and data conform strictly to the official Google Weather API:
https://weather.googleapis.com/v1/forecast/days:lookup
"""

import logging
import os
import threading
import time
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

GOOGLE_WEATHER_URL = "https://weather.googleapis.com/v1/forecast/days:lookup"

# Client timeouts for Google Weather API calls
_TIMEOUT = httpx.Timeout(connect=8.0, read=12.0, write=5.0, pool=5.0)

# Force IPv4 transport for cloud hosts where IPv6 handshake stalls
try:
    _TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0")
except Exception:  # pragma: no cover
    _TRANSPORT = None

# Cache TTL: 6 hours
CACHE_TTL_SECONDS = 6 * 3600

# Cache storage: (round(lat, 3), round(lon, 3)) -> {"expires_at": float, "data": dict, "cached_at": float}
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


def clear_weather_cache():
    """Clear in-memory cache and inflight events (used in unit tests)."""
    with _CACHE_LOCK:
        _WEATHER_CACHE.clear()
    with _INFLIGHT_LOCK:
        _INFLIGHT_EVENTS.clear()


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
    """Call Google Weather API days:lookup endpoint and parse the up-to-10-day forecast.

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
    }

    client_kwargs = {"timeout": _TIMEOUT}
    if _TRANSPORT is not None:
        client_kwargs["transport"] = _TRANSPORT

    try:
        with httpx.Client(**client_kwargs) as client:
            response = client.get(GOOGLE_WEATHER_URL, params=params)

            if response.status_code in (400, 401, 403):
                # Never log the secret key
                logger.error("[weather] Google Weather API error (%s): %s", response.status_code, response.text[:200])
                raise RuntimeError("Google Weather API request or authentication failed.")

            if response.status_code == 429:
                logger.warning("[weather] Google Weather API rate limit reached (429).")
                raise RuntimeError("Weather provider rate limit reached. Please try again shortly.")

            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, Exception) as exc:
        logger.error("[weather] Google Weather request failed: %s", type(exc).__name__)
        raise RuntimeError("Weather provider is temporarily unavailable.") from exc

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
    """Return daily forecast data from Google Weather API with 6-hour caching.

    Respects the 10-day forecast horizon. If dates are beyond the horizon,
    returns real data for available dates and a polite inline forecast notice
    without inventing data or throwing unhandled errors.
    """
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")

    today = date.today()

    if end_date < today:
        raise ValueError("Weather forecasts are not available for past dates.")

    effective_start = max(start_date, today)
    effective_end = end_date

    coord_key = (round(latitude, 3), round(longitude, 3))

    # 1. Check in-process cache (valid for 6 hours)
    now = time.monotonic()
    cached_days = None
    with _CACHE_LOCK:
        entry = _WEATHER_CACHE.get(coord_key)
        if entry and now < entry["expires_at"]:
            cached_days = entry["data"]

    # 2. In-flight request deduplication
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
            with _CACHE_LOCK:
                entry = _WEATHER_CACHE.get(coord_key)
                if entry:
                    cached_days = entry["data"]

        if cached_days is None:
            try:
                days_by_date = _fetch_google_weather(latitude, longitude)
                with _CACHE_LOCK:
                    _WEATHER_CACHE[coord_key] = {
                        "expires_at": time.monotonic() + CACHE_TTL_SECONDS,
                        "data": days_by_date,
                        "cached_at": time.monotonic(),
                    }
                cached_days = days_by_date
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

    forecast_notice = FORECAST_NOTICE_TEXT if has_partial else None

    return {
        "latitude": latitude,
        "longitude": longitude,
        "source": "Google Weather",
        "daily": forecasts,
        "has_partial_forecast": has_partial,
        "forecast_notice": forecast_notice,
    }
