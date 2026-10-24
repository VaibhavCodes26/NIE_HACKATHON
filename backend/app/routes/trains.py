"""RailRadar-powered station, train, seat-availability and fare endpoints."""
from __future__ import annotations

import re
from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query

from app.services.railradar_service import RailRadarAPIError, railradar_get

router = APIRouter(prefix="/api/trains", tags=["trains"])
STATION_CODE_RE = re.compile(r"^[A-Z0-9]{2,10}$")
TRAIN_NUMBER_RE = re.compile(r"^\d{5}$")

TravelClass = Literal[
    "1A", "2A", "3A", "3E", "CC", "EC", "EA", "FC", "SL", "2S",
    "VS", "CH", "SH", "VC", "EV",
]
QuotaCode = Literal["GN", "TQ", "PT", "LD", "DF", "FT", "SS", "YU", "DP", "HP", "PH"]
StationLimit = Literal[5, 10, 20, 50]


def _raise_api_error(exc: RailRadarAPIError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _validate_station_code(value: str, label: str) -> str:
    normalized = value.strip().upper()
    if not STATION_CODE_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=422,
            detail=f"{label} must be a valid station code (2–10 letters or digits). Search for the station by name if unsure.",
        )
    return normalized


def _validate_train_number(value: str) -> str:
    normalized = value.strip()
    if not TRAIN_NUMBER_RE.fullmatch(normalized):
        raise HTTPException(status_code=422, detail="Train number must contain 5 digits.")
    return normalized


def _validate_journey_date(value: date) -> date:
    if value < date.today():
        raise HTTPException(status_code=422, detail="Journey date cannot be in the past.")
    return value


@router.get("/stations")
async def search_railway_stations(
    q: str = Query(min_length=2, max_length=80, description="Station name, city, or code"),
    limit: int = Query(default=10, ge=5, le=50),
):
    """Autocomplete Indian railway stations using RailRadar's station lookup."""
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Enter at least two characters to search stations.")
    try:
        return await railradar_get(
            "/lookup/search/stations",
            {"q": query, "limit": limit},
        )
    except RailRadarAPIError as exc:
        _raise_api_error(exc)


@router.get("/between")
async def search_trains_between_stations(
    from_station: str = Query(alias="from", min_length=2, max_length=10),
    to_station: str = Query(alias="to", min_length=2, max_length=10),
    journey_date: date | None = Query(default=None, alias="date"),
):
    """Return the provider's train list for a station pair and optional date."""
    source = _validate_station_code(from_station, "Source station code")
    destination = _validate_station_code(to_station, "Destination station code")
    if source == destination:
        raise HTTPException(status_code=422, detail="Source and destination stations must be different.")

    params = {}
    if journey_date is not None:
        params["date"] = _validate_journey_date(journey_date).isoformat()

    try:
        return await railradar_get(
            f"/trains/between/{quote(source, safe='')}/{quote(destination, safe='')}",
            params,
        )
    except RailRadarAPIError as exc:
        _raise_api_error(exc)


async def _search_train_booking_data(
    endpoint: Literal["seats", "fare"],
    number: str,
    source: str,
    destination: str,
    journey_date: date,
    class_code: TravelClass,
    quota_code: QuotaCode,
):
    train_number = _validate_train_number(number)
    from_code = _validate_station_code(source, "Source station code")
    to_code = _validate_station_code(destination, "Destination station code")
    if from_code == to_code:
        raise HTTPException(status_code=422, detail="Source and destination stations must be different.")
    checked_date = _validate_journey_date(journey_date)

    params = {
        "source": from_code,
        "destination": to_code,
        "journeyDate": checked_date.isoformat(),
        "classCode": class_code,
        "quotaCode": quota_code,
    }
    try:
        return await railradar_get(f"/trains/{train_number}/{endpoint}", params)
    except RailRadarAPIError as exc:
        _raise_api_error(exc)


@router.get("/{number}/seats")
async def get_train_seat_availability(
    number: str,
    source: str = Query(min_length=2, max_length=10),
    destination: str = Query(min_length=2, max_length=10),
    journey_date: date = Query(alias="journeyDate"),
    class_code: TravelClass = Query(default="3A", alias="classCode"),
    quota_code: QuotaCode = Query(default="GN", alias="quotaCode"),
):
    """Return RailRadar's documented seat availability calendar."""
    return await _search_train_booking_data(
        "seats", number, source, destination, journey_date, class_code, quota_code
    )


@router.get("/{number}/fare")
async def get_train_fare(
    number: str,
    source: str = Query(min_length=2, max_length=10),
    destination: str = Query(min_length=2, max_length=10),
    journey_date: date = Query(alias="journeyDate"),
    class_code: TravelClass = Query(default="3A", alias="classCode"),
    quota_code: QuotaCode = Query(default="GN", alias="quotaCode"),
):
    """Return RailRadar's itemized fare response for the chosen train/class."""
    return await _search_train_booking_data(
        "fare", number, source, destination, journey_date, class_code, quota_code
    )
