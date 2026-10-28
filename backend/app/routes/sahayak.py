from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.services import sahayak_service as svc
from app.services import tts_service

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
def ask(req: AskRequest):
    ctx = req.context.model_dump(exclude_none=True) if req.context else None
    return svc.ask(req.query, req.language, req.scenario, ctx)


@router.get("/tts")
def kannada_tts(text: str = Query(..., min_length=1, max_length=500)):
    """Return synthesized Kannada MP3 speech for the given phrase with HTTP caching headers."""
    try:
        audio_content = tts_service.synthesize_kannada_speech(text)
        return Response(
            content=audio_content,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=604800, immutable",
                "Content-Disposition": 'inline; filename="kannada_phrase.mp3"',
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Kannada speech audio is temporarily unavailable.",
        )
