"""Small async client for the official RailRadar REST API.

The API key is read only by the backend from RAILRADAR_API_KEY.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

# Load backend/.env when python-dotenv is installed (it is commonly used by this app).
# Runtime environment variables still take precedence over .env values.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:
    pass

RAILRADAR_BASE_URL = "https://api.railradar.in/v1"
TIMEOUT_SECONDS = 18.0


class RailRadarAPIError(Exception):
    """Provider failure with a safe HTTP status and user-facing message."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _safe_error_message(status_code: int) -> tuple[int, str]:
    """Map provider status codes without leaking raw upstream data or secrets."""
    if status_code in (401, 403):
        return 502, "RailRadar rejected the API credentials. Check RAILRADAR_API_KEY."
    if status_code == 400:
        return 422, "RailRadar rejected the search parameters. Check the station codes and journey details."
    if status_code == 404:
        return 404, "RailRadar did not find a matching train, station, or fare record."
    if status_code == 429:
        return 429, "RailRadar request limit reached. Please retry later."
    if status_code in (408, 504):
        return 504, "RailRadar took too long to respond. Please retry."
    if status_code >= 500:
        return 503, "RailRadar is temporarily unavailable. Please retry later."
    return 502, "RailRadar could not complete this request."


async def railradar_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call a RailRadar GET endpoint and return its validated JSON envelope."""
    api_key = os.getenv("RAILRADAR_API_KEY", "").strip()
    if not api_key:
        raise RailRadarAPIError(
            503,
            "RailRadar is not configured. Add RAILRADAR_API_KEY to backend/.env and restart FastAPI.",
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    url = f"{RAILRADAR_BASE_URL}{path}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params or {}, headers=headers)
    except httpx.TimeoutException as exc:
        raise RailRadarAPIError(504, "RailRadar request timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise RailRadarAPIError(502, "Could not connect to RailRadar. Please retry.") from exc

    if not response.is_success:
        status_code, message = _safe_error_message(response.status_code)
        raise RailRadarAPIError(status_code, message)

    try:
        payload = response.json()
    except ValueError as exc:
        raise RailRadarAPIError(502, "RailRadar returned an invalid response.") from exc

    if not isinstance(payload, dict):
        raise RailRadarAPIError(502, "RailRadar returned an unexpected response format.")

    # RailRadar documents a {success, data, meta} envelope. Do not treat an
    # unsuccessful envelope as successful data, even when HTTP status is 200.
    if payload.get("success") is False:
        provider_error = payload.get("error") or {}
        code = str(provider_error.get("code", "")).upper()
        message_map = {
            "NOT_FOUND": (404, "RailRadar did not find a matching record."),
            "INVALID_PARAMETER": (422, "RailRadar rejected the search parameters."),
            "UNAUTHORIZED": (502, "RailRadar rejected the API credentials. Check RAILRADAR_API_KEY."),
            "RATE_LIMITED": (429, "RailRadar request limit reached. Please retry later."),
        }
        status_code, message = message_map.get(code, (502, "RailRadar could not complete this request."))
        raise RailRadarAPIError(status_code, message)

    if "data" not in payload:
        raise RailRadarAPIError(502, "RailRadar response did not contain data.")

    return payload
