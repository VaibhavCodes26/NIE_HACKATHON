from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services import drishti_service

router = APIRouter(prefix="/api/drishti", tags=["drishti"])


class ScanRequest(BaseModel):
    image: str = Field(..., description="Data URL (e.g. data:image/jpeg;base64,...)")
    language: str = Field("en", description="Target language code (e.g. en, hi, mr, ta, te)")


class DrishtiResponse(BaseModel):
    success: bool
    kind: str
    source_language: str
    target_language: str
    detected_text: str
    translated_text: str
    summary: str
    items: list
    message: str
    cached: Optional[bool] = False


@router.post("/translate", response_model=DrishtiResponse)
async def translate_image(
    file: UploadFile = File(..., description="Uploaded image file (JPEG, PNG, WebP)"),
    target_language: str = Form("en", description="Target language code (e.g., en, hi, mr)"),
):
    """
    Primary endpoint for Namma Drishti:
    Accepts multipart/form-data image upload and target language.
    Extracts Kannada text via Gemini Vision OCR and translates in a single request.
    """
    if not file:
        raise HTTPException(status_code=400, detail="An image file is required.")

    mime_type = file.content_type or ""
    # Normalize common aliases
    if mime_type == "image/jpg":
        mime_type = "image/jpeg"

    if mime_type not in drishti_service.ALLOWED_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type ({mime_type}). Please upload a JPEG, PNG, or WebP image.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded image: {str(e)}")

    if len(content) > drishti_service.MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image size exceeds 10 MB limit. Please upload a smaller image.",
        )

    try:
        result = drishti_service.process_image(
            raw_bytes=content,
            mime_type=mime_type,
            target_language=target_language,
        )
        return result
    except drishti_service.ScanError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal translation error. Please try again.")


@router.post("/scan", response_model=DrishtiResponse)
def scan_base64(req: ScanRequest):
    """
    Base64 / Data-URL fallback endpoint for Namma Drishti.
    """
    try:
        return drishti_service.scan(req.image, req.language)
    except drishti_service.ScanError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan error: {str(e)}")
