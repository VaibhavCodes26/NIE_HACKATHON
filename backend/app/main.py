
"""FastAPI application for NammaPrayana itinerary previews."""
import httpx 
from collections import Counter
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
import json
from app.database import create_tables, get_db
from app.models import Attraction, Destination, FoodSpot
from app.schemas import (
    ItineraryDay,
    ItineraryPreviewResponse,
    ItineraryRequest,
    ItineraryStop,
    ItineraryWarning,
)
from app.services.stays_service import recommend_stays
app = FastAPI(
    title="NammaPrayana API",
    description="Karnataka travel itinerary planning API",
    version="1.0.0",
)

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

    # Fetch attractions for the selected destinations.
    attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id.in_(request.destinations))
        .order_by(Attraction.visit_order, Attraction.id)
    ).all()

    attractions_by_destination = {
        destination_id: []
        for destination_id in request.destinations
    }

    for attraction in attractions:
        attractions_by_destination[attraction.destination_id].append(attraction)

    # Match attractions to the selected interests when possible.
    selected_interests = {
        interest.value.lower()
        for interest in request.interests
    }

    filtered_attractions = {}

    for destination_id, destination_attractions in attractions_by_destination.items():
        matching = [
            attraction
            for attraction in destination_attractions
            if selected_interests
            and any(
                tag.lower() in selected_interests
                for tag in (attraction.interest_tags or [])
            )
        ]

        # Do not leave a destination empty merely because no tags match.
        filtered_attractions[destination_id] = (
            matching if matching else destination_attractions
        )

    # Allocate consecutive days to each destination.
    destination_count = len(selected_destinations)
    base_days = duration_days // destination_count
    extra_days = duration_days % destination_count

    days = []
    warnings = []
    current_date = request.start_date
    needs_verification = False
    empty_destinations = []

    for index, destination in enumerate(selected_destinations):
        assigned_days = base_days + (1 if index < extra_days else 0)
        destination_attractions = filtered_attractions[destination.id]

        if not destination_attractions and not selected_mode:
            empty_destinations.append(destination.name)
            
    
        for local_day in range(assigned_days):
            day_number = len(days) + 1

            # Cycle through available attractions to fill different trip days.
            start_index = local_day * 3
            daily_attractions = destination_attractions[
                start_index:start_index + 3
            ]

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

   
    # Fetch attractions belonging to the selected destinations.
    all_attractions = db.scalars(
        select(Attraction)
        .where(Attraction.destination_id.in_(request.destinations))
        .order_by(Attraction.destination_id, Attraction.visit_order, Attraction.id)
    ).all()

    all_attractions_by_id = {
        attraction.id: attraction for attraction in all_attractions
    }

    selected_mode = request.selected_attraction_ids is not None

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
    """Return all food spots for the requested city."""
    spots = db.scalars(
        select(FoodSpot)
        .where(FoodSpot.city == city)
        .order_by(FoodSpot.spot_id)
    ).all()

    if not spots:
        raise HTTPException(
            status_code=404,
            detail=f"No food spots found for city '{city}'.",
        )

    return {
        "foods": [
            {
                "id": spot.id,
                "spot_id": spot.spot_id,
                "city": spot.city,
                "name": spot.famous_food_spot,
                "category": spot.tourist_attraction,
                "description": spot.description,
                "speciality_dish": spot.speciality_dish,
                "restaurant_name": spot.famous_food_spot,
                "rating": spot.rating_as_per_google,
                "map_url": spot.google_maps_link,
                "is_must_try": spot.rating_as_per_google is not None
                    and float(spot.rating_as_per_google.split("/")[0].strip()) >= 4.4,
            }
            for spot in spots
        ]
    }
    
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
