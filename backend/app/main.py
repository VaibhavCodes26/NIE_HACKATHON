
"""FastAPI application for NammaPrayana itinerary previews."""
import httpx 
from collections import Counter
from datetime import date, timedelta
from app.services.weather_service import get_weather_forecast
from fastapi import Depends, FastAPI, HTTPException,Query
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
import json
from app.services.gemini_service import generate_itinerary
from app.database import create_tables, get_db
from app.models import Attraction, Destination, FoodSpot
from app.schemas import (
    ItineraryDay,
    ItineraryPreviewResponse,
    ItineraryRequest,
    ItineraryStop,
    ItineraryWarning,
)
from app.routes.trains import router as trains_router
from app.services.stays_service import recommend_stays
app = FastAPI(
    title="NammaPrayana API",
    description="Karnataka travel itinerary planning API",
    version="1.0.0",
)
app.include_router(trains_router)

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
@app.get("/api/weather/forecast")
def weather_forecast(
    latitude: float | None = None,
    longitude: float | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    destination: str | None = None,
    date_param: date | None = Query(default=None, alias="date"),
):
    # Support the existing frontend: destination + date.
    if latitude is None or longitude is None:
        if not destination:
            raise HTTPException(
                status_code=422,
                detail="Provide a destination or latitude and longitude.",
            )

        key = destination.strip().lower()
        coordinates = WEATHER_COORDINATES.get(key)

        if coordinates is None:
            # Also match destination display names from the database.
            with next(get_db()) as db:
                destinations = db.scalars(
                    select(Destination).where(Destination.is_active.is_(True))
                ).all()

            match = next(
                (
                    item for item in destinations
                    if item.name.strip().lower() == key
                ),
                None,
            )

            if match is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Weather coordinates unavailable for destination: {destination}",
                )

            coordinates = WEATHER_COORDINATES.get(match.id)

        if coordinates is None:
            raise HTTPException(
                status_code=404,
                detail=f"Weather coordinates unavailable for destination: {destination}",
            )

        latitude, longitude = coordinates

    start_date = start_date or date_param or date.today()
    end_date = end_date or start_date

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

#ai generated itinerary 
@app.post("/api/itineraries/generate")
def generate_ai_itinerary(
    request: ItineraryRequest,
    db: Session = Depends(get_db),
):
    duration_days = (request.end_date - request.start_date).days + 1

   
    # Preserve the destination order selected by the user.
    destination_map = {
        item.id: item
        for item in db.scalars(
            select(Destination).where(
                Destination.id.in_(request.destinations),
                Destination.is_active.is_(True),
            )
        ).all()
    }

    missing_destinations = [
        item for item in request.destinations
        if item not in destination_map
    ]

    if missing_destinations:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown destinations: {missing_destinations}",
        )

    selected_destinations = [
        destination_map[item] for item in request.destinations
    ]

    # Load attractions only from the selected destinations.
    all_attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id.in_(request.destinations))
        .order_by(Attraction.destination_id, Attraction.visit_order, Attraction.id)
    ).all()

    attraction_map = {item.id: item for item in all_attractions}

    if request.selected_attraction_ids:
        missing_ids = [
            item for item in request.selected_attraction_ids
            if item not in attraction_map
        ]

        if missing_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid selected attraction IDs: {missing_ids}",
            )

        attractions = [
            attraction_map[item]
            for item in request.selected_attraction_ids
        ]
    else:
        interests = {item.value.lower() for item in request.interests}

        matching = [
            item for item in all_attractions
            if any(
                tag.lower() in interests
                for tag in (item.interest_tags or [])
            )
        ]

        # Keep the prompt compact if the user did not select specific spots.
        attractions = (matching or all_attractions)[:40]

    attraction_records = [
        {
            "id": item.id,
            "name": item.name,
            "destination_id": item.destination_id,
            "category": item.category,
            "description": item.description,
            "suggested_time": item.suggested_time,
            "estimated_duration_minutes": item.estimated_duration_minutes,
            "source_status": item.source_status,
        }
        for item in attractions
    ]

    # Fetch food records from the database for selected destinations.
    food_rows = db.scalars(
        select(FoodSpot).order_by(FoodSpot.city, FoodSpot.spot_id)
    ).all()

    destination_keys = {
        item.id.replace("-", " ").lower() for item in selected_destinations
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
            food_records.append({
                "id": spot.id,
                "city": spot.city,
                "name": spot.famous_food_spot,
               "category": "Local food",
                "description": spot.description,
                "speciality_dish": spot.speciality_dish,
            })

    # Assign consecutive dates to destinations, matching the existing preview.
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

        coordinates = WEATHER_COORDINATES.get(destination.id)

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
                weather_records.append({
                    "destination": destination.name,
                    **item,
                })

        except (ValueError, RuntimeError):
            weather_warnings.append(
                f"Weather could not be checked for {destination.name} "
                f"({first_date} to {last_date})."
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

    # Make missing weather visible instead of implying every date was checked.
    result["weather_warnings"] = weather_warnings
    result["weather_source"] = "Open-Meteo"
    result["generation_status"] = "ai_generated"

    return result



@app.post(
    "/api/itineraries/preview",
    response_model=ItineraryPreviewResponse,
)
def preview_itinerary(
    request: ItineraryRequest,
    db: Session = Depends(get_db),
):
    # Calculate inclusive trip duration.
    duration_days = (request.end_date - request.start_date).days + 1

    if len(request.destinations) > duration_days:
        raise HTTPException(
            status_code=422,
            detail="Choose at least one travel day for every selected destination.",
        )

    # Retrieve destinations in the exact order selected by the user.
    destination_map = {
        destination.id: destination
        for destination in db.scalars(
            select(Destination).where(
                Destination.id.in_(request.destinations),
                Destination.is_active.is_(True),
            )
        ).all()
    }

    missing = [
        destination_id
        for destination_id in request.destinations
        if destination_id not in destination_map
    ]

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown or inactive destination IDs: {', '.join(missing)}",
        )

    selected_destinations = [
        destination_map[destination_id]
        for destination_id in request.destinations
    ]

   
   
    # Fetch attractions belonging to the selected destinations.
    all_attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id.in_(request.destinations))
        .order_by(Attraction.destination_id, Attraction.visit_order, Attraction.id)
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

        # Preserve the order in which the frontend submits selected IDs.
        attractions = [
            all_attractions_by_id[attraction_id]
            for attraction_id in requested_ids
        ]
    else:
        # Backward-compatible automatic selection for older clients.
        attractions = all_attractions

    attractions_by_destination = {
        destination_id: []
        for destination_id in request.destinations
    }

    for attraction in attractions:
        attractions_by_destination[attraction.destination_id].append(
            attraction
        )

    # Apply interest matching only to automatic recommendations.
    # Explicitly selected attractions must never be filtered out.
    selected_interests = {
        interest.value.lower()
        for interest in request.interests
    }

    if not selected_mode and selected_interests:
        for destination_id, destination_attractions in (
            attractions_by_destination.items()
        ):
            matching = [
                attraction
                for attraction in destination_attractions
                if any(
                    tag.lower() in selected_interests
                    for tag in (attraction.interest_tags or [])
                )
            ]

            if matching:
                attractions_by_destination[destination_id] = matching

    destination_count = len(selected_destinations)
    base_days = duration_days // destination_count
    extra_days = duration_days % destination_count

    days = []
    warnings = []
    current_date = request.start_date
    needs_verification = False
    empty_destinations = []
    overloaded_days = []

    for index, destination in enumerate(selected_destinations):
        assigned_days = base_days + (1 if index < extra_days else 0)
        destination_attractions = attractions_by_destination[
            destination.id
        ]

        if not destination_attractions and not selected_mode:
            empty_destinations.append(destination.name)

        # Spread every selected attraction across this destination's days.
        # Unlike the previous slice(start_index:start_index + 3) logic,
        # this does not silently drop selected attractions.
        daily_attraction_groups = [
            destination_attractions[local_day::assigned_days]
            for local_day in range(assigned_days)
        ]

        for local_day, daily_attractions in enumerate(
            daily_attraction_groups
        ):
            day_number = len(days) + 1

            if len(daily_attractions) > 3:
                overloaded_days.append(day_number)

            stops = []

            for attraction in daily_attractions:
                source_status = (
                    "curated_reference"
                    if attraction.source_status == "curated_reference"
                    else "needs_verification"
                )

                if source_status == "needs_verification":
                    needs_verification = True

                stops.append(
                    ItineraryStop(
                        attraction_id=attraction.id,
                        name=attraction.name,
                        category=attraction.category,
                        description=attraction.description,
                        suggested_time=attraction.suggested_time,
                        source_status=source_status,
                    )
                )

            days.append(
                ItineraryDay(
                    day_number=day_number,
                    date=current_date,
                    destination_id=destination.id,
                    destination_name=destination.name,
                    stops=stops,
                    intercity_transfer_from_previous=None,
                    weather_status="not_requested",
                )
            )

            current_date += timedelta(days=1)

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

    if overloaded_days:
        warnings.append(
            ItineraryWarning(
                code="BUSY_DAYS",
                message=(
                    "Some days contain more than three selected attractions "
                    f"(day numbers: {overloaded_days}). All selected places "
                    "are retained, but consider adding time or removing stops."
                ),
                severity="warning",
            )
        )


    if needs_verification:
        warnings.append(
            ItineraryWarning(
                code="VERIFY_ATTRACTIONS",
                message=(
                    "Some attraction details are awaiting verification. "
                    "Check local access, opening hours and travel conditions before visiting."
                ),
                severity="info",
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

    destination_names = [destination.name for destination in selected_destinations]

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
    )
class RouteLocation(BaseModel):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: RouteLocation
    destination: RouteLocation
    travelDate: date = Field(default_factory=date.today)



@app.post("/api/routes")
async def get_transport_routes(request: RouteRequest):
    
    if request.travelDate < date.today():
        raise HTTPException(
            status_code=422,
            detail="Travel date cannot be in the past.",
        )

    origin = request.origin
    destination = request.destination

    # Never return invented road distances if routing fails.
    try:
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{origin.lng},{origin.lat};"
            f"{destination.lng},{destination.lat}"
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                params={"overview": "false", "steps": "true"},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError("No road route returned by provider.")

        road_route = data["routes"][0]
        distance_km = road_route["distance"] / 1000
        duration_min = road_route["duration"] / 60

        fare_min = round((80 + distance_km * 18) * 0.8 / 10) * 10
        fare_max = round((80 + distance_km * 18) * 1.2 / 10) * 10

        taxi = {
            "available": True,
            "distanceKm": distance_km,
            "durationMin": duration_min,
            "fare": f"₹{fare_min}–₹{fare_max}",
            "fareNote": "Indicative estimate only; not a live taxi quote.",
            "summary": (
                f"Road route from {origin.name} to {destination.name}, "
                "calculated using OpenStreetMap-based OSRM routing."
            ),
            "steps": [
                f"Start at {origin.name}.",
                f"Follow the calculated road route for approximately "
                f"{distance_km:.1f} km.",
                f"Arrive at {destination.name}.",
            ],
            "notes": [
                "Road distance and duration are provider estimates, not live traffic predictions.",
                "Taxi fare is an indicative estimate, not an Ola/Uber quote.",
                "Actual fares may vary with traffic, tolls, waiting and surge pricing.",
            ],
            "extra": [
                {"label": "Routing source", "value": "OSRM / OpenStreetMap"},
                {"label": "Fare status", "value": "Indicative estimate"},
            ],
        }

    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        taxi = {
            "available": False,
            "distanceKm": 0,
            "durationMin": 0,
            "fare": "Unavailable",
            "fareNote": "Road routing provider did not return a verified route.",
            "summary": "Road route could not be calculated right now.",
            "steps": ["Please retry when the routing service is available."],
            "notes": [
                "No estimated distance or duration is being substituted.",
                "The routing service may be temporarily unavailable.",
            ],
            "extra": [],
        }

    def unavailable_mode(message, source_url):
        return {
            "available": False,
            "sourceUrl": source_url,
            "distanceKm": 0,
            "durationMin": 0,
            "fare": "Not verified",
            "fareNote": "No verified fare available.",
            "summary": message,
            "steps": [
                "Check the official operator source for this journey."
            ],
            "notes": [
                f"Official source: {source_url}",
                "Schedules, availability and fares have not been verified by this endpoint.",
            ],
            "extra": [],
        }

    return {
        
            "walking": unavailable_mode(
                "Walking directions are not available from the current routing provider.",
                "https://www.openstreetmap.org/directions",
            ),
            "train": unavailable_mode(
                f"Train schedules for {origin.name} to {destination.name} "
                f"on {request.travelDate.isoformat()} have not been verified.",
                "https://www.indianrail.gov.in/enquiry/TBIS/TrainBetweenImportantStations.jsp",
            ),
            "bus": unavailable_mode(
                f"Bus schedules for {origin.name} to {destination.name} "
                f"on {request.travelDate.isoformat()} have not been verified.",
                "https://www.ksrtc.in/",
            ),
            "metro": unavailable_mode(
                "Metro availability depends on the selected origin and destination. "
                "A verified metro route is not available from this endpoint.",
                "https://english.bmrc.co.in/",
            ),

        }
@app.get("/api/food/cities")
def get_food_cities(db: Session = Depends(get_db)):
    """Return the distinct city names that have food spots in the database."""
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

        # Remove alternate names in parentheses for matching.
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
            rating_value = float(
                spot.rating_as_per_google.split("/")[0].strip()
            ) if spot.rating_as_per_google else None
        except (ValueError, AttributeError):
            rating_value = None

        foods.append({
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
            "is_must_try": rating_value is not None
                and rating_value >= 4.4,
        })

    return {"foods": foods}

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
        # Log exc in production; don't expose secrets or provider errors.
        raise HTTPException(
            status_code=502,
            detail=(
                f"Stay recommendations failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc
