
"""Compact daily weather forecasts from Open-Meteo."""

import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Separate connect and read timeouts so a slow DNS/TCP handshake on IPv6-broken
# networks (e.g. Render free tier) cannot hang the endpoint indefinitely.
_TIMEOUT = httpx.Timeout(connect=8.0, read=12.0, write=5.0, pool=5.0)

# Force IPv4 transport so the request doesn't stall on hosts where IPv6
# connectivity to api.open-meteo.com is broken (Render, some cloud VMs).
# httpx uses its own HTTP/1.1 stack and is NOT affected by the socket.getaddrinfo
# monkey-patch in net_utils.py, so we must configure transport directly.
try:
    _TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0")
except Exception:  # pragma: no cover — older httpx versions
    _TRANSPORT = None


def get_weather_forecast(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict:
    """Return daily forecast data without inventing unavailable weather."""

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

    try:
        client_kwargs = {"timeout": _TIMEOUT}
        if _TRANSPORT is not None:
            client_kwargs["transport"] = _TRANSPORT
        with httpx.Client(**client_kwargs) as client:
            response = client.get(OPEN_METEO_URL, params=params)
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
    except ValueError:
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
