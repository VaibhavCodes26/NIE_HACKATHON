from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services import sahayak_service as svc
from app.services.rate_limiter import rate_limit_sahayak

router = APIRouter(prefix="/api/sahayak", tags=["sahayak"])


class TripContext(BaseModel):
    city: Optional[str] = None
    travellers: Optional[int] = None
    budget: Optional[int] = None
    style: Optional[str] = None


class AskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    language: Literal["en", "hi", "mr"] = "en"
    scenario: Optional[str] = None
    context: Optional[TripContext] = None


@router.get("/scenarios")
def scenarios():
    return svc.SCENARIOS


@router.get("/phrases")
def phrases(scenario: str):
    """Instant, no-AI path for scenario cards. Works even if Gemini is down."""
    return svc.phrases_for_scenario(scenario)


@router.post("/ask")
def ask(
    req: AskRequest,
    _rate_limit: None = Depends(rate_limit_sahayak),
):
    ctx = req.context.model_dump(exclude_none=True) if req.context else None
    return svc.ask(req.query, req.language, req.scenario, ctx)

