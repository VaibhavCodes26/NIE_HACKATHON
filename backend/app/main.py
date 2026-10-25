
"""FastAPI application for NammaPrayana."""

import asyncio
import json
import os
from datetime import date, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import create_tables, get_db
from app.models import Attraction, Destination, FoodSpot
from app.routes.trains import router as trains_router
from app.routes.sahayak import router as sahayak_router
from app.routes.gati import router as gati_router
from app.routes.drishti import router as drishti_router
from app.schemas import (
    DeferredAttraction,
    ItineraryDay,
    ItineraryPreviewResponse,
    ItineraryRequest,
    ItineraryStop,
    ItineraryWarning,
)
from app.services import gati_service
from app.services.gemini_service import generate_itinerary
from app.services.railradar_service import railradar_get
from app.services.stays_service import recommend_stays
from app.services.weather_service import get_weather_forecast


def _extract_pacing_profile(request: ItineraryRequest) -> tuple[str, dict[str, bool]]:
    """Extract explicit or implicit pace and profile settings from the request."""
    pace = str(getattr(request, "pace", "balanced") or "balanced").strip().lower()
    profile = dict(getattr(request, "profile", {}) or {})

    adj = str(getattr(request, "adjustment_request", "") or "")
    if adj:
        adj_lower = adj.lower()
        if "senior" in adj_lower:
            profile["senior"] = True
        if "pregnant" in adj_lower or "pregnancy" in adj_lower:
            profile["pregnant"] = True
        if "child" in adj_lower or "kid" in adj_lower:
            profile["child"] = True
        if "mobility" in adj_lower or "accessibility" in adj_lower or "wheelchair" in adj_lower:
            profile["mobility"] = True
        if "relaxed" in adj_lower or "easy pace" in adj_lower or "less walking" in adj_lower or "easy-pace" in adj_lower or "less-walking" in adj_lower:
            pace = "relaxed"
        elif "packed" in adj_lower or "fast" in adj_lower:
            pace = "packed"

    return pace, profile


# Load E:\NIE_HACKATHON\backend\.env regardless of the terminal's working directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

app = FastAPI(
    title="NammaPrayana API",
    description="Karnataka travel itinerary planning API",
    version="1.0.0",
)

app.include_router(trains_router)
app.include_router(sahayak_router)
app.include_router(gati_router)
app.include_router(drishti_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()


@app.get("/")
def home():
    return {
        "message": "Welcome to NammaPrayana API",
        "status": "running",
    }


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

WEATHER_COORDINATES = {
    "badami": (15.9149, 75.6768),
    "hampi": (15.3350, 76.4600),
    "mysuru": (12.2958, 76.6394),
    "bengaluru": (12.9716, 77.5946),
    "coorg": (12.4244, 75.7382),
    "chikkamagaluru": (13.3161, 75.7720),
    "mangaluru": (12.9141, 74.8560),
    "udupi": (13.3409, 74.7421),
    "gokarna": (14.5479, 74.3188),
    "dandeli": (15.2470, 74.6290),
    "shivamogga": (13.9299, 75.5681),
    "belur-halebidu": (13.1650, 75.8650),
    "vijayapura": (16.8302, 75.7100),
    "bidar": (17.9149, 77.5046),
    "chitradurga": (14.2251, 76.3980),
    "belagavi": (15.8497, 74.4977),
    "hubballi": (15.3647, 75.1240),
    "hassan": (13.0068, 76.0996),
}


def _resolve_coordinates(destination: str, db: Session) -> tuple[float, float] | None:
    """Resolve coordinates for destination using key, aliases or DB lookup."""
    key = destination.strip().lower()
    if key in WEATHER_COORDINATES:
        return WEATHER_COORDINATES[key]

    aliases = {
        "bangalore": "bengaluru",
        "mysore": "mysuru",
        "badami & aihole": "badami",
        "badami and aihole": "badami",
        "chikmagalur": "chikkamagaluru",
        "chikmagaluru": "chikkamagaluru",
        "shimoga": "shivamogga",
        "bijapur": "vijayapura",
        "hubli": "hubballi",
        "belgaum": "belagavi",
        "kodagu": "coorg",
        "madikeri": "coorg",
        "belur": "belur-halebidu",
        "halebidu": "belur-halebidu",
        "belur and halebidu": "belur-halebidu",
        "belur & halebidu": "belur-halebidu",
    }
    if key in aliases and aliases[key] in WEATHER_COORDINATES:
        return WEATHER_COORDINATES[aliases[key]]

    for alias_key, target in aliases.items():
        if alias_key in key or key in alias_key:
            if target in WEATHER_COORDINATES:
                return WEATHER_COORDINATES[target]

    destinations = db.scalars(
        select(Destination).where(Destination.is_active.is_(True))
    ).all()

    for item in destinations:
        clean_name = item.name.split("(")[0].strip().lower()
        if key == item.id.lower() or key == item.name.strip().lower() or key == clean_name:
            if item.id in WEATHER_COORDINATES:
                return WEATHER_COORDINATES[item.id]

    # Partial match on destinations
    for item in destinations:
        if item.id in key or key in item.id or item.name.lower() in key or key in item.name.lower():
            if item.id in WEATHER_COORDINATES:
                return WEATHER_COORDINATES[item.id]

    return None


@app.get("/api/weather/forecast")
def weather_forecast(
    latitude: float | None = None,
    longitude: float | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    destination: str | None = None,
    date_param: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    if latitude is None or longitude is None:
        if not destination:
            raise HTTPException(
                status_code=422,
                detail="Provide a destination or latitude and longitude.",
            )

        coordinates = _resolve_coordinates(destination, db)

        if coordinates is None:
            raise HTTPException(
                status_code=404,
                detail=f"Weather coordinates unavailable for destination: {destination}",
            )

        latitude, longitude = coordinates

    start_date = start_date or date_param or date.today()
    end_date = end_date or start_date

    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="End date must be on or after start date.",
        )

    try:
        return get_weather_forecast(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="Weather forecast is temporarily unavailable.",
        ) from exc


# ---------------------------------------------------------------------------
# Destinations and attractions
# ---------------------------------------------------------------------------

@app.get("/api/destinations")
def get_destinations(db: Session = Depends(get_db)):
    destinations = db.scalars(
        select(Destination)
        .where(Destination.is_active.is_(True))
        .order_by(Destination.name)
    ).all()

    return [
        {
            "id": destination.id,
            "name": destination.name,
            "region": destination.region,
        }
        for destination in destinations
    ]


@app.get("/api/destinations/{destination_id}/attractions")
def get_attractions(
    destination_id: str,
    db: Session = Depends(get_db),
):
    destination = db.get(Destination, destination_id)

    if destination is None or not destination.is_active:
        raise HTTPException(status_code=404, detail="Destination not found.")

    attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id == destination_id)
        .order_by(Attraction.visit_order, Attraction.id)
    ).all()

    return [
        {
            "id": attraction.id,
            "name": attraction.name,
            "category": attraction.category,
            "description": attraction.description,
            "suggested_time": attraction.suggested_time,
            "interest_tags": attraction.interest_tags or [],
            "estimated_duration_minutes": attraction.estimated_duration_minutes,
            "is_must_visit": attraction.is_must_visit,
            "source_status": attraction.source_status,
        }
        for attraction in attractions
    ]


# ---------------------------------------------------------------------------
# AI-generated itinerary
# ---------------------------------------------------------------------------

@app.post("/api/itineraries/generate")
def generate_ai_itinerary(
    request: ItineraryRequest,
    db: Session = Depends(get_db),
):
    duration_days = (request.end_date - request.start_date).days + 1

    if duration_days < 1:
        raise HTTPException(
            status_code=422,
            detail="End date must be on or after start date.",
        )

    if not request.destinations:
        raise HTTPException(
            status_code=422,
            detail="Select at least one destination.",
        )

    active_destinations = db.scalars(
        select(Destination).where(Destination.is_active.is_(True))
    ).all()

    dest_by_key: dict[str, Destination] = {}
    for dest in active_destinations:
        dest_by_key[dest.id.lower()] = dest
        dest_by_key[dest.name.lower()] = dest
        clean_name = dest.name.split("(")[0].strip().lower()
        dest_by_key[clean_name] = dest
        dest_by_key[dest.id.replace("-", " ").lower()] = dest
        dest_by_key[dest.name.replace("&", "and").lower()] = dest

    selected_destinations = []
    missing_destinations = []
    for raw_dest in request.destinations:
        key = str(raw_dest).strip().lower()
        matched = dest_by_key.get(key)
        if matched is None:
            for k, d in dest_by_key.items():
                if k in key or key in k:
                    matched = d
                    break
        if matched:
            if matched not in selected_destinations:
                selected_destinations.append(matched)
        else:
            missing_destinations.append(raw_dest)

    if missing_destinations:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown destinations: {missing_destinations}",
        )

    selected_dest_ids = [item.id for item in selected_destinations]

    all_attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id.in_(selected_dest_ids))
        .order_by(
            Attraction.destination_id,
            Attraction.visit_order,
            Attraction.id,
        )
    ).all()

    attraction_map = {item.id: item for item in all_attractions}

    if request.selected_attraction_ids:
        attractions = [
            attraction_map[item]
            for item in request.selected_attraction_ids
            if item in attraction_map
        ]
        if not attractions:
            attractions = all_attractions[:40]
    else:
        interests = {item.value.lower() for item in request.interests}

        matching = [
            item
            for item in all_attractions
            if any(
                tag.lower() in interests
                for tag in (item.interest_tags or [])
            )
        ]

        attractions = (matching or all_attractions)[:40]

    dest_id_to_name = {item.id: item.name for item in selected_destinations}

    attraction_records = [
        {
            "id": item.id,
            "name": item.name,
            "destination_id": item.destination_id,
            "city": dest_id_to_name.get(item.destination_id, item.destination_id),
            "category": item.category,
            "description": item.description,
            "suggested_time": item.suggested_time,
            "estimated_duration_minutes": item.estimated_duration_minutes,
            "duration_hours": (item.estimated_duration_minutes / 60.0) if item.estimated_duration_minutes else None,
            "source_status": item.source_status,
            "is_must_visit": item.is_must_visit,
            "tags": item.interest_tags or [],
        }
        for item in attractions
    ]

    # Calculate authoritative Namma Gati pacing schedule before Gemini
    pace_choice, profile_choice = _extract_pacing_profile(request)
    gati_plan = gati_service.plan(
        stops=attraction_records,
        n_days=duration_days,
        profile=profile_choice,
        cities=[item.name for item in selected_destinations],
        pace=pace_choice,
        start_date=request.start_date,
    )

    food_rows = db.scalars(
        select(FoodSpot).order_by(FoodSpot.city, FoodSpot.spot_id)
    ).all()

    destination_keys = {
        item.id.replace("-", " ").lower()
        for item in selected_destinations
    } | {
        item.name.replace("&", " ").replace("-", " ").lower()
        for item in selected_destinations
    }

    food_records = []

    for spot in food_rows:
        city_key = spot.city.replace("&", " ").replace("-", " ").lower()

        if any(
            city_key in key or key in city_key
            for key in destination_keys
            if city_key and key
        ):
            food_records.append(
                {
                    "id": spot.id,
                    "city": spot.city,
                    "name": spot.famous_food_spot,
                    "category": "Local food",
                    "description": spot.description,
                    "speciality_dish": spot.speciality_dish,
                }
            )

    weather_records = []
    weather_warnings = []

    base_days = duration_days // len(selected_destinations)
    extra_days = duration_days % len(selected_destinations)
    day_offset = 0

    for index, destination in enumerate(selected_destinations):
        assigned_days = base_days + (1 if index < extra_days else 0)
        first_date = request.start_date + timedelta(days=day_offset)
        last_date = first_date + timedelta(days=assigned_days - 1)
        day_offset += assigned_days

        coordinates = _resolve_coordinates(destination.id, db) or _resolve_coordinates(destination.name, db)

        if not coordinates:
            weather_warnings.append(
                f"Weather coordinates are unavailable for {destination.name}."
            )
            continue

        try:
            forecast = get_weather_forecast(
                latitude=coordinates[0],
                longitude=coordinates[1],
                start_date=first_date,
                end_date=last_date,
            )

            for item in forecast.get("daily", []):
                weather_records.append(
                    {
                        "destination": destination.name,
                        **item,
                    }
                )

        except (ValueError, RuntimeError) as exc:
            weather_warnings.append(
                f"Weather forecast unavailable for {destination.name} "
                f"({first_date} to {last_date}): {exc}."
            )

    try:
        result = generate_itinerary(
            destinations=[item.name for item in selected_destinations],
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            traveller_count=request.traveller_count,
            travel_style=request.travel_style.value,
            total_budget=request.total_budget,
            interests=[item.value for item in request.interests],
            attractions=attraction_records,
            food_spots=food_records,
            weather_data=weather_records,
            adjustment_request=request.adjustment_request,
            gati_plan=gati_plan,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI itinerary generation failed: {exc}",
        ) from exc
    except Exception as exc:
        print(f"[ITINERARY AI ERROR] {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail="The AI itinerary service is temporarily unavailable.",
        ) from exc

    result["gati"] = gati_plan
    result["deferred"] = gati_plan.get("deferred", [])
    result["weather_warnings"] = weather_warnings
    result["weather_source"] = "Open-Meteo"
    result["generation_status"] = "ai_generated"

    return result


# ---------------------------------------------------------------------------
# Itinerary preview
# ---------------------------------------------------------------------------

@app.post(
    "/api/itineraries/preview",
    response_model=ItineraryPreviewResponse,
)
def preview_itinerary(
    request: ItineraryRequest,
    db: Session = Depends(get_db),
):
    duration_days = (request.end_date - request.start_date).days + 1

    if duration_days < 1:
        raise HTTPException(
            status_code=422,
            detail="End date must be on or after start date.",
        )

    if not request.destinations:
        raise HTTPException(
            status_code=422,
            detail="Select at least one destination.",
        )

    if len(request.destinations) > duration_days:
        raise HTTPException(
            status_code=422,
            detail="Choose at least one travel day for every selected destination.",
        )

    active_destinations = db.scalars(
        select(Destination).where(Destination.is_active.is_(True))
    ).all()

    dest_by_key: dict[str, Destination] = {}
    for dest in active_destinations:
        dest_by_key[dest.id.lower()] = dest
        dest_by_key[dest.name.lower()] = dest
        clean_name = dest.name.split("(")[0].strip().lower()
        dest_by_key[clean_name] = dest
        dest_by_key[dest.id.replace("-", " ").lower()] = dest
        dest_by_key[dest.name.replace("&", "and").lower()] = dest

    selected_destinations = []
    missing = []
    for raw_dest in request.destinations:
        key = str(raw_dest).strip().lower()
        matched = dest_by_key.get(key)
        if matched is None:
            for k, d in dest_by_key.items():
                if k in key or key in k:
                    matched = d
                    break
        if matched:
            if matched not in selected_destinations:
                selected_destinations.append(matched)
        else:
            missing.append(raw_dest)

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown or inactive destination IDs: {', '.join(missing)}",
        )

    selected_dest_ids = [item.id for item in selected_destinations]

    all_attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id.in_(selected_dest_ids))
        .order_by(
            Attraction.destination_id,
            Attraction.visit_order,
            Attraction.id,
        )
    ).all()

    all_attractions_by_id = {
        attraction.id: attraction for attraction in all_attractions
    }

    selected_mode = bool(request.selected_attraction_ids)

    if selected_mode:
        requested_ids = request.selected_attraction_ids

        if len(requested_ids) != len(set(requested_ids)):
            raise HTTPException(
                status_code=422,
                detail="Duplicate attraction IDs are not allowed.",
            )

        missing_ids = [
            attraction_id
            for attraction_id in requested_ids
            if attraction_id not in all_attractions_by_id
        ]

        if missing_ids:
            raise HTTPException(
                status_code=422,
                detail=(
                    "These attraction IDs do not belong to the selected "
                    f"destinations or do not exist: {missing_ids}"
                ),
            )

        attractions = [
            all_attractions_by_id[attraction_id]
            for attraction_id in requested_ids
        ]
    else:
        attractions = all_attractions

    dest_id_to_name = {destination.id: destination.name for destination in selected_destinations}

    attraction_records = [
        {
            "id": attraction.id,
            "name": attraction.name,
            "destination_id": attraction.destination_id,
            "city": dest_id_to_name.get(attraction.destination_id, attraction.destination_id),
            "category": attraction.category,
            "description": attraction.description,
            "suggested_time": attraction.suggested_time,
            "estimated_duration_minutes": attraction.estimated_duration_minutes,
            "duration_hours": (attraction.estimated_duration_minutes / 60.0) if attraction.estimated_duration_minutes else None,
            "source_status": attraction.source_status,
            "is_must_visit": attraction.is_must_visit,
            "tags": attraction.interest_tags or [],
        }
        for attraction in attractions
    ]

    pace_choice, profile_choice = _extract_pacing_profile(request)
    gati_plan = gati_service.plan(
        stops=attraction_records,
        n_days=duration_days,
        profile=profile_choice,
        cities=[d.name for d in selected_destinations],
        pace=pace_choice,
        start_date=request.start_date,
    )

    days = []
    warnings = []

    for day_idx, gd in enumerate(gati_plan.get("days", []), start=1):
        d_name = gd.get("destination") or (" + ".join(gd.get("cities", [])) if gd.get("cities") else "Karnataka")
        matched_dest_id = ""
        if gd.get("cities"):
            first_c = gd["cities"][0].lower()
            for d_obj in selected_destinations:
                if d_obj.name.lower() in first_c or first_c in d_obj.name.lower():
                    matched_dest_id = d_obj.id
                    break
        if not matched_dest_id and selected_destinations:
            matched_dest_id = selected_destinations[min(day_idx - 1, len(selected_destinations) - 1)].id

        day_date = request.start_date + timedelta(days=day_idx - 1)

        day_stops = [
            ItineraryStop(
                attraction_id=s.get("id"),
                name=s.get("name", "Attraction"),
                category=s.get("category", "Tourist attraction"),
                description=s.get("description", ""),
                suggested_time=s.get("suggested_time") or "Morning",
                source_status=s.get("source_status", "curated_reference"),
                effort=s.get("effort"),
                level=s.get("level"),
                city=s.get("city"),
            )
            for s in gd.get("stops", [])
        ]

        days.append(
            ItineraryDay(
                day_number=day_idx,
                date=day_date,
                destination_id=matched_dest_id,
                destination_name=d_name,
                stops=day_stops,
                effort_total=gd.get("total", 0),
                capacity=gd.get("capacity", gati_plan.get("summary", {}).get("capacity", 110)),
                status=gd.get("status", "ok"),
                notes=gd.get("notes", []),
            )
        )

    for w in gati_plan.get("warnings", []):
        warnings.append(
            ItineraryWarning(
                code="GATI_PACING",
                message=w,
                severity="info",
            )
        )

    if selected_mode and not request.selected_attraction_ids:
        warnings.append(
            ItineraryWarning(
                code="NO_SELECTED_ATTRACTIONS",
                message=(
                    "No tourist spots were selected. Return to Route Discovery "
                    "and select attractions, or regenerate using automatic "
                    "recommendations."
                ),
                severity="warning",
            )
        )

    warnings.append(
        ItineraryWarning(
            code="PREVIEW_ONLY",
            message=(
                "This is an itinerary preview, not a booking. "
                "Transport schedules, accommodation availability and live prices "
                "are not confirmed by this endpoint."
            ),
            severity="info",
        )
    )

    destination_names = [
        destination.name for destination in selected_destinations
    ]

    deferred_objs = [
        DeferredAttraction(
            id=d_item.get("id"),
            name=d_item.get("name", "Deferred attraction"),
            city=d_item.get("city"),
            category=d_item.get("category"),
            effort=d_item.get("effort"),
            level=d_item.get("level"),
            code=d_item.get("code"),
            reason=d_item.get("reason"),
        )
        for d_item in gati_plan.get("deferred", [])
    ]

    return ItineraryPreviewResponse(
        status="preview",
        title="Your Karnataka Journey: " + " → ".join(destination_names),
        start_date=request.start_date,
        end_date=request.end_date,
        duration_days=duration_days,
        destinations=selected_destinations,
        traveller_count=request.traveller_count,
        travel_style=request.travel_style,
        total_budget=request.total_budget,
        budget_per_traveller=round(
            request.total_budget / request.traveller_count, 2
        ),
        interests=[interest.value for interest in request.interests],
        days=days,
        warnings=warnings,
        data_policy=(
            "Attractions come from the local NammaPrayana reference database. "
            "Interest matching is best-effort. This preview does not confirm "
            "live weather, bookings, transport schedules or current prices."
        ),
        gati=gati_plan,
        deferred=deferred_objs,
    )


# ---------------------------------------------------------------------------
# Route directions
# ---------------------------------------------------------------------------

class RouteLocation(BaseModel):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: RouteLocation
    destination: RouteLocation
    travelDate: date = Field(default_factory=date.today)


ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
ROUTES_FIELD_MASK = (
    "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline,"
    "routes.description,routes.travelAdvisory.transitFare,"
    "routes.legs.steps.navigationInstruction.instructions,"
    "routes.legs.steps.distanceMeters,routes.legs.steps.staticDuration,"
    "routes.legs.steps.transitDetails"
)

def unavailable_mode(message: str, source_url: str):
    return {
        "available": False,
        "sourceUrl": source_url,
        "distanceKm": 0,
        "durationMin": 0,
        "fare": "Unavailable",
        "fareNote": "No verified direct route available.",
        "summary": message,
        "steps": ["No direct route available for this mode."],
        "notes": [f"Official source: {source_url}"],
        "extra": [],
    }


async def _fetch_google_route(
    client: httpx.AsyncClient,
    routes_api_key: str | None,
    origin: RouteLocation,
    destination: RouteLocation,
    travel_mode: str,
    routing_preference: str | None = None,
    transit_preferences: dict | None = None,
    origin_address: str | None = None,
    destination_address: str | None = None,
) -> dict | None:
    if not routes_api_key:
        return None

    # Use address if provided, otherwise fall back to lat/lng
    if origin_address:
        origin_payload = {"address": origin_address}
    else:
        origin_payload = {
            "location": {
                "latLng": {
                    "latitude": origin.lat,
                    "longitude": origin.lng,
                }
            }
        }

    if destination_address:
        destination_payload = {"address": destination_address}
    else:
        destination_payload = {
            "location": {
                "latLng": {
                    "latitude": destination.lat,
                    "longitude": destination.lng,
                }
            }
        }

    payload = {
        "origin": origin_payload,
        "destination": destination_payload,
        "travelMode": travel_mode,
        "languageCode": "en",
    }
    if routing_preference:
        payload["routingPreference"] = routing_preference
    if transit_preferences:
        payload["transitPreferences"] = transit_preferences

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": routes_api_key,
        "X-Goog-FieldMask": ROUTES_FIELD_MASK,
    }

    try:
        response = await client.post(
            ROUTES_API_URL,
            json=payload,
            headers=headers,
        )
        if response.status_code == 200:
            return response.json()
        print(f"Google Routes API {travel_mode} returned status {response.status_code}: {response.text[:200]}")
    except Exception as exc:
        print(f"Google Routes API {travel_mode} failed: {type(exc).__name__}: {exc}")
    return None


@app.post("/api/routes")
async def get_transport_routes(request: RouteRequest):
    if request.travelDate < date.today():
        raise HTTPException(
            status_code=422,
            detail="Travel date cannot be in the past.",
        )

    origin = request.origin
    destination = request.destination
    routes_api_key = os.getenv("ROUTES_API_KEY")

    async with httpx.AsyncClient(timeout=20.0) as client:
        taxi_task = _fetch_google_route(
            client, routes_api_key, origin, destination,
            travel_mode="DRIVE",
            routing_preference="TRAFFIC_AWARE",
        )
        walking_task = _fetch_google_route(
            client, routes_api_key, origin, destination,
            travel_mode="WALK",
        )
        # Bus: use DRIVING mode between KSRTC bus terminal addresses for accurate intercity routing
        bus_origin_address = f"KSRTC Bus Terminal, {origin.name}, Karnataka, India"
        bus_destination_address = f"KSRTC Bus Terminal, {destination.name}, Karnataka, India"
        bus_task = _fetch_google_route(
            client, routes_api_key, origin, destination,
            travel_mode="DRIVE",
            routing_preference="TRAFFIC_AWARE",
            origin_address=bus_origin_address,
            destination_address=bus_destination_address,
        )
        metro_task = _fetch_google_route(
            client, routes_api_key, origin, destination,
            travel_mode="TRANSIT",
            transit_preferences={"allowedTravelModes": ["SUBWAY"]},
        )

        taxi_data, walking_data, bus_data, metro_data = await asyncio.gather(
            taxi_task, walking_task, bus_task, metro_task
        )

    train = unavailable_mode(
        f"Train schedules for {origin.name} to {destination.name} "
        f"on {request.travelDate.isoformat()} have not been verified.",
        "https://www.irctc.co.in/nget/train-search",
    )

    # 1. Taxi / Driving (Google Routes API with TRAFFIC_AWARE)
    taxi = unavailable_mode(
        f"Driving route from {origin.name} to {destination.name} could not be calculated.",
        "https://maps.google.com",
    )
    if taxi_data and taxi_data.get("routes"):
        r = taxi_data["routes"][0]
        distance_km = r.get("distanceMeters", 0) / 1000.0
        duration_sec = float(r.get("duration", "0s").removesuffix("s") or 0)
        duration_min = round(duration_sec / 60.0)
        polyline = r.get("polyline", {}).get("encodedPolyline", "")

        fare_min = round((80 + distance_km * 18) * 0.8 / 10) * 10
        fare_max = round((80 + distance_km * 18) * 1.2 / 10) * 10

        steps = [
            step["navigationInstruction"]["instructions"]
            for leg in r.get("legs", [])
            for step in leg.get("steps", [])
            if step.get("navigationInstruction", {}).get("instructions")
        ]
        if not steps:
            steps = [
                f"Start at {origin.name}.",
                f"Follow the road route for approximately {distance_km:.1f} km with live traffic awareness.",
                f"Arrive at {destination.name}.",
            ]

        taxi = {
            "available": True,
            "distanceKm": round(distance_km, 2),
            "durationMin": duration_min,
            "polyline": polyline,
            "fare": f"₹{fare_min:,}–₹{fare_max:,}",
            "fareNote": "Indicative estimate only; not a live taxi quote.",
            "summary": (
                f"Road route from {origin.name} to {destination.name}, "
                "calculated using Google Routes API with live traffic."
            ),
            "steps": steps,
            "notes": [
                "Route duration accounts for live traffic conditions.",
                "Taxi fare is an indicative estimate, not an Ola/Uber quote.",
                "Actual fares may vary with traffic, waiting time, and tolls.",
            ],
            "extra": [
                {"label": "Routing source", "value": "Google Routes API (Traffic Aware)"},
                {"label": "Fare status", "value": "Indicative estimate"},
            ],
        }

    # 2. Walking (Google Routes API)
    walking = unavailable_mode(
        f"Walking route from {origin.name} to {destination.name} could not be calculated.",
        "https://maps.google.com",
    )
    if walking_data and walking_data.get("routes"):
        r = walking_data["routes"][0]
        distance_km = r.get("distanceMeters", 0) / 1000.0
        duration_sec = float(r.get("duration", "0s").removesuffix("s") or 0)
        duration_min = round(duration_sec / 60.0)
        polyline = r.get("polyline", {}).get("encodedPolyline", "")

        steps = [
            step["navigationInstruction"]["instructions"]
            for leg in r.get("legs", [])
            for step in leg.get("steps", [])
            if step.get("navigationInstruction", {}).get("instructions")
        ]
        if not steps:
            steps = [
                f"Follow pedestrian paths from {origin.name} to {destination.name}."
            ]

        warning = "Long distance: walking is not recommended for this journey." if distance_km > 25 else None

        walking = {
            "available": True,
            "distanceKm": round(distance_km, 2),
            "durationMin": duration_min,
            "polyline": polyline,
            "fare": "Free",
            "fareNote": "Pedestrian walking route.",
            "warning": warning,
            "summary": (
                f"Walking route from {origin.name} to {destination.name}, "
                "calculated using Google Routes API."
            ),
            "steps": steps,
            "notes": [
                "Distance and duration are Google Routes API estimates.",
            ],
            "extra": [
                {"label": "Routing source", "value": "Google Routes API"},
            ],
        }

    # 3. Bus (DRIVE mode between KSRTC bus terminals for accurate intercity routing)
    bus = unavailable_mode(
        f"No direct KSRTC bus route found between {origin.name} and {destination.name}.",
        "https://www.ksrtc.in/",
    )
    # Vehicle types considered true metro/subway (still needed for metro section below)
    _SUBWAY_VEHICLE_TYPES = {"SUBWAY", "METRO_RAIL", "MONORAIL", "TRAM"}

    if bus_data and bus_data.get("routes"):
        r = bus_data["routes"][0]
        distance_km = r.get("distanceMeters", 0) / 1000.0
        duration_sec = float(r.get("duration", "0s").removesuffix("s") or 0)
        duration_min = round(duration_sec / 60.0)
        polyline = r.get("polyline", {}).get("encodedPolyline", "")

        # Boarding and alighting at KSRTC terminals
        dep_terminal = f"KSRTC Bus Terminal, {origin.name}"
        arr_terminal = f"KSRTC Bus Terminal, {destination.name}"

        # Fare estimate for KSRTC (approx ₹1.5 per km for ordinary, ₹2.2 for express)
        fare_min = round(distance_km * 1.5 / 10) * 10
        fare_max = round(distance_km * 2.2 / 10) * 10

        steps = [
            f"Proceed to {dep_terminal}.",
            f"Board KSRTC intercity bus towards {destination.name}.",
        ]
        nav_steps = [
            step["navigationInstruction"]["instructions"]
            for leg in r.get("legs", [])
            for step in leg.get("steps", [])
            if step.get("navigationInstruction", {}).get("instructions")
        ]
        if nav_steps:
            steps.extend(nav_steps)
        steps.append(f"Arrive at {arr_terminal}.")

        bus = {
            "available": True,
            "distanceKm": round(distance_km, 2),
            "durationMin": duration_min,
            "polyline": polyline,
            "fare": f"₹{fare_min:,}–₹{fare_max:,}",
            "fareNote": "Indicative KSRTC fare estimate (ordinary to express). Check ksrtc.in for exact fares.",
            "summary": (
                f"KSRTC intercity bus from {dep_terminal} to {arr_terminal}. "
                f"Route calculated via Google Routes API (DRIVE between bus terminals)."
            ),
            "steps": steps,
            "notes": [
                "Board at KSRTC Bus Terminal. Verify schedule at ksrtc.in or redbus.in.",
                "Fare is an estimate based on per-km rates; actual fares vary by service class.",
                "Route duration is driving time between terminals; bus journey may differ.",
            ],
            "extra": [
                {"label": "Boarding terminal", "value": dep_terminal},
                {"label": "Alighting terminal", "value": arr_terminal},
                {"label": "Operator", "value": "KSRTC Karnataka"},
                {"label": "Routing source", "value": "Google Routes API (DRIVE, bus terminals)"},
            ],
        }

    # 4. Metro (Google Routes API TRANSIT with allowedTravelModes: [SUBWAY])
    metro = unavailable_mode(
        f"No direct metro route found between {origin.name} and {destination.name}.",
        "https://english.bmrc.co.in/",
    )
    if metro_data and metro_data.get("routes"):
        r = metro_data["routes"][0]
        # Only mark available if the API actually returned subway/metro-type steps.
        # The API sometimes returns BUS steps even when SUBWAY is requested for
        # intercity journeys; those must be rejected here.
        transit_steps = [
            step for leg in r.get("legs", [])
            for step in leg.get("steps", [])
            if "transitDetails" in step
            and step["transitDetails"].get("transitLine", {}).get("vehicle", {}).get("type")
            in _SUBWAY_VEHICLE_TYPES
        ]
        if transit_steps:
            distance_km = r.get("distanceMeters", 0) / 1000.0
            duration_sec = float(r.get("duration", "0s").removesuffix("s") or 0)
            duration_min = round(duration_sec / 60.0)
            polyline = r.get("polyline", {}).get("encodedPolyline", "")

            first_td = transit_steps[0].get("transitDetails", {})
            t_line = first_td.get("transitLine", {})
            metro_line = t_line.get("nameShort") or t_line.get("name") or "Metro"
            dep_station = first_td.get("stopDetails", {}).get("departureStop", {}).get("name")
            arr_station = first_td.get("stopDetails", {}).get("arrivalStop", {}).get("name")
            stop_count = first_td.get("stopCount")
            agencies = t_line.get("agencies", [])
            agency_name = agencies[0].get("name") if agencies else "BMRCL"

            fare_obj = r.get("travelAdvisory", {}).get("transitFare")
            if fare_obj and fare_obj.get("units"):
                curr = "₹" if fare_obj.get("currencyCode") == "INR" else f"{fare_obj.get('currencyCode')} "
                fare_str = f"{curr}{fare_obj['units']}"
                fare_note = "Official metro fare reported by provider."
            else:
                fare_str = "Not published"
                fare_note = "Fare not published by transit agency."

            steps = []
            for leg in r.get("legs", []):
                for step in leg.get("steps", []):
                    if "transitDetails" in step:
                        td = step["transitDetails"]
                        tl = td.get("transitLine", {})
                        l_name = tl.get("nameShort") or tl.get("name") or "Metro"
                        ds = td.get("stopDetails", {}).get("departureStop", {}).get("name") or "station"
                        as_ = td.get("stopDetails", {}).get("arrivalStop", {}).get("name") or "destination station"
                        sc = td.get("stopCount")
                        sc_text = f" ({sc} stations)" if sc else ""
                        steps.append(f"Board {l_name} at {ds} towards {td.get('headsign', 'terminal')}{sc_text}.")
                        steps.append(f"Alight at {as_}.")
                    elif step.get("navigationInstruction", {}).get("instructions"):
                        steps.append(step["navigationInstruction"]["instructions"])

            if not steps:
                steps = [f"Take metro line {metro_line} from {dep_station or origin.name} to {arr_station or destination.name}."]

            extra = [{"label": "Metro line", "value": metro_line}]
            if dep_station:
                extra.append({"label": "Boarding", "value": dep_station})
            if arr_station:
                extra.append({"label": "Alighting", "value": arr_station})
            if stop_count:
                extra.append({"label": "Stations", "value": f"{stop_count} stations"})

            metro = {
                "available": True,
                "distanceKm": round(distance_km, 2),
                "durationMin": duration_min,
                "polyline": polyline,
                "fare": fare_str,
                "fareNote": fare_note,
                "summary": (
                    f"Metro transit via {metro_line} from {dep_station or origin.name} "
                    f"to {arr_station or destination.name}."
                ),
                "steps": steps,
                "notes": [
                    "Metro route calculated using Google Routes API.",
                    f"Operated by {agency_name}.",
                ],
                "extra": extra,
            }

    modes = {
        "taxi": taxi,
        "walking": walking,
        "train": train,
        "bus": bus,
        "metro": metro,
    }

    primary_distance = next(
        (m["distanceKm"] for m in [taxi, train, bus, metro, walking] if m.get("available")),
        0,
    )

    return {
        "distanceKm": primary_distance,
        "isIllustrative": False,
        "modes": modes,
    }


# ---------------------------------------------------------------------------
# Food spots
# ---------------------------------------------------------------------------

@app.get("/api/food/cities")
def get_food_cities(db: Session = Depends(get_db)):
    """Return distinct city names that have food spots in the database."""
    rows = db.execute(
        select(FoodSpot.city).distinct().order_by(FoodSpot.city)
    ).scalars().all()

    return {
        "cities": [{"id": name, "name": name} for name in rows]
    }


@app.get("/api/food/spots")
def get_food_spots(city: str, db: Session = Depends(get_db)):
    """Return food spots for a city, supporting frontend destination IDs."""

    def normalize_city(value: str) -> str:
        value = value.strip().lower()

        aliases = {
            "mysore": "mysuru",
            "hubli": "hubballi",
            "belgaum": "belagavi",
            "shimoga": "shivamogga",
            "kodagu": "coorg",
            "bijapur": "vijayapura",
        }

        primary_name = value.split("(")[0].strip()
        return aliases.get(primary_name, primary_name)

    requested_city = normalize_city(city)

    all_spots = db.scalars(
        select(FoodSpot).order_by(FoodSpot.city, FoodSpot.spot_id)
    ).all()

    spots = [
        spot
        for spot in all_spots
        if normalize_city(spot.city) == requested_city
    ]

    if not spots:
        raise HTTPException(
            status_code=404,
            detail=f"No food spots found for city '{city}'.",
        )

    foods = []

    for spot in spots:
        try:
            rating_value = (
                float(spot.rating_as_per_google.split("/")[0].strip())
                if spot.rating_as_per_google
                else None
            )
        except (ValueError, AttributeError):
            rating_value = None

        foods.append(
            {
                "id": spot.id,
                "spot_id": spot.spot_id,
                "city": spot.city,
                "name": spot.famous_food_spot,
                "category": "Local food",
                "description": spot.description,
                "speciality_dish": spot.speciality_dish,
                "restaurant_name": spot.famous_food_spot,
                "rating": spot.rating_as_per_google,
                "map_url": spot.google_maps_link,
                "is_must_try": (
                    rating_value is not None and rating_value >= 4.4
                ),
            }
        )

    return {"foods": foods}


# ---------------------------------------------------------------------------
# Stays
# ---------------------------------------------------------------------------

class StaysRequest(BaseModel):
    destinations: list[str] = Field(min_length=1, max_length=8)
    start_date: date
    end_date: date
    traveller_count: int = Field(ge=1, le=30)
    travel_style: str = Field(
        pattern=r"^(budget|comfortable|premium|ultra-premium)$"
    )
    total_budget: int = Field(gt=0, le=10000000)


@app.post("/api/stays/recommendations")
def get_stay_recommendations(request: StaysRequest):
    if request.start_date < date.today():
        raise HTTPException(
            status_code=422,
            detail="Check-in date cannot be in the past.",
        )

    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=422,
            detail="Check-out date must be on or after check-in.",
        )

    try:
        return recommend_stays(
            destinations=request.destinations,
            start_date=request.start_date,
            end_date=request.end_date,
            traveller_count=request.traveller_count,
            travel_style=request.travel_style,
            total_budget=request.total_budget,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not process stay recommendations.",
        ) from exc
    except Exception as exc:
        print(f"[STAYS ERROR] {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Stay recommendations failed. Check the backend logs.",
        ) from exc
