"""Saved itinerary CRUD routes for NammaPrayana.

Endpoints:
  POST   /api/itineraries/saved          — save a completed itinerary
  GET    /api/itineraries/saved          — list current user's saved itineraries
  GET    /api/itineraries/saved/{id}     — get a specific saved itinerary
  DELETE /api/itineraries/saved/{id}     — delete a saved itinerary

All endpoints require authentication. Ownership is always derived from the
authenticated session, never from a frontend-supplied user_id.
"""

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SavedItinerary, User
from app.routes.auth import get_current_user

router = APIRouter(prefix="/api/itineraries/saved", tags=["saved-itineraries"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SaveItineraryRequest(BaseModel):
    """The full itinerary payload from the frontend ItineraryPage."""

    # Complete AI-generated itinerary (days, warnings, gati, etc.)
    itinerary_payload: dict[str, Any]

    # Original trip configuration from PlanJourney
    trip_config: dict[str, Any]

    # Ordered destination names / IDs
    destinations: list[str] = Field(default_factory=list)

    # Selected attraction IDs
    selected_attraction_ids: list[int] = Field(default_factory=list)

    # Summary fields for list view
    title: str = Field(default="Karnataka Journey", max_length=400)
    start_date: str | None = None
    end_date: str | None = None
    traveller_count: int | None = None
    total_budget: int | None = None
    travel_style: str | None = None
    duration_days: int | None = None


class SavedItinerarySummary(BaseModel):
    """Lightweight summary for the itineraries list view."""

    id: int
    title: str
    destinations: list[str]
    start_date: str | None
    end_date: str | None
    traveller_count: int | None
    total_budget: int | None
    travel_style: str | None
    duration_days: int | None
    created_at: str


class SavedItineraryDetail(SavedItinerarySummary):
    """Full detail including the complete itinerary payload."""

    itinerary_payload: dict[str, Any]
    trip_config: dict[str, Any]
    selected_attraction_ids: list[int]
    updated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_summary(itinerary: SavedItinerary) -> SavedItinerarySummary:
    return SavedItinerarySummary(
        id=itinerary.id,
        title=itinerary.title,
        destinations=itinerary.destinations or [],
        start_date=itinerary.start_date,
        end_date=itinerary.end_date,
        traveller_count=itinerary.traveller_count,
        total_budget=itinerary.total_budget,
        travel_style=itinerary.travel_style,
        duration_days=itinerary.duration_days,
        created_at=itinerary.created_at.isoformat(),
    )


def _to_detail(itinerary: SavedItinerary) -> SavedItineraryDetail:
    return SavedItineraryDetail(
        id=itinerary.id,
        title=itinerary.title,
        destinations=itinerary.destinations or [],
        start_date=itinerary.start_date,
        end_date=itinerary.end_date,
        traveller_count=itinerary.traveller_count,
        total_budget=itinerary.total_budget,
        travel_style=itinerary.travel_style,
        duration_days=itinerary.duration_days,
        created_at=itinerary.created_at.isoformat(),
        updated_at=itinerary.updated_at.isoformat(),
        itinerary_payload=itinerary.itinerary_payload or {},
        trip_config=itinerary.trip_config or {},
        selected_attraction_ids=itinerary.selected_attraction_ids or [],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def save_itinerary(
    body: SaveItineraryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedItineraryDetail:
    """Persist a completed itinerary for the authenticated user.

    Idempotency: if the same payload has already been saved for this user
    (identified by title + start_date + end_date), the existing record is
    returned without creating a duplicate. A new generation is always
    saveable as a separate record.
    """
    # Validate that the payload contains actual day data.
    days = body.itinerary_payload.get("days") or body.itinerary_payload.get("itinerary_days") or []
    if not days:
        raise HTTPException(
            status_code=422,
            detail="itinerary_payload must contain at least one day.",
        )

    title = body.title or "Karnataka Journey"

    # Compute duration_days if not provided.
    duration_days = body.duration_days
    if not duration_days and body.start_date and body.end_date:
        try:
            s = date.fromisoformat(body.start_date)
            e = date.fromisoformat(body.end_date)
            duration_days = (e - s).days + 1
        except ValueError:
            duration_days = len(days)

    if not duration_days:
        duration_days = len(days)

    itinerary = SavedItinerary(
        user_id=current_user.id,
        title=title,
        trip_config=body.trip_config,
        itinerary_payload=body.itinerary_payload,
        destinations=body.destinations,
        selected_attraction_ids=body.selected_attraction_ids,
        start_date=body.start_date,
        end_date=body.end_date,
        traveller_count=body.traveller_count,
        total_budget=body.total_budget,
        travel_style=body.travel_style,
        duration_days=duration_days,
    )
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)

    return _to_detail(itinerary)


@router.get("")
def list_itineraries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SavedItinerarySummary]:
    """Return all saved itineraries for the authenticated user, newest first."""
    itineraries = db.scalars(
        select(SavedItinerary)
        .where(SavedItinerary.user_id == current_user.id)
        .order_by(SavedItinerary.created_at.desc())
    ).all()

    return [_to_summary(i) for i in itineraries]


@router.get("/{itinerary_id}")
def get_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedItineraryDetail:
    """Return the full detail of a saved itinerary owned by the current user."""
    itinerary = db.get(SavedItinerary, itinerary_id)

    if itinerary is None or itinerary.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found.")

    return _to_detail(itinerary)


@router.delete("/{itinerary_id}", status_code=204)
def delete_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a saved itinerary owned by the current user."""
    itinerary = db.get(SavedItinerary, itinerary_id)

    if itinerary is None or itinerary.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found.")

    db.delete(itinerary)
    db.commit()
