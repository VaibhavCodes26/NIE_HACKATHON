from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.services import gati_service

router = APIRouter(prefix="/api/gati", tags=["gati"])


class Stop(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: Optional[int | str] = None
    name: str
    city: Optional[str] = None
    category: Optional[str] = None
    destination_id: Optional[str] = None
    description: Optional[str] = None
    suggested_time: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    duration_hours: Optional[float] = None
    effort: Optional[int | float] = None


class Profile(BaseModel):
    senior: bool = False
    pregnant: bool = False
    child: bool = False
    mobility: bool = False


class PlanRequest(BaseModel):
    stops: list[Stop] = Field(default_factory=list, max_length=100)
    days: int = Field(ge=1, le=30)
    cities: list[str] = []
    profile: Profile = Profile()
    pace: str = "balanced"
    start_date: Optional[str] = None


@router.post("/plan")
def plan(req: PlanRequest):
    """
    Live stamina-aware pacing plan.
    Deterministic, pure Python, zero AI tokens.
    """
    stops = [s.model_dump() for s in req.stops]
    return gati_service.plan(
        stops=stops,
        n_days=req.days,
        profile=req.profile.model_dump(),
        cities=req.cities,
        pace=req.pace,
        start_date=req.start_date,
    )
