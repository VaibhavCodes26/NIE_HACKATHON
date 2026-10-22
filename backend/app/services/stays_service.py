
"""AI-assisted stay recommendations grounded in Google Search."""

import json
import os
from datetime import date
from urllib.parse import urlparse

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL_NAME = os.getenv(
    "GEMINI_STAYS_MODEL",
    "gemini-3.5-flash-lite",
)

ALLOWED_STYLES = {
    "budget",
    "comfortable",
    "premium",
    "ultra-premium",
}


def _https_url(value):
    """Accept only syntactically valid HTTPS URLs."""
    if not isinstance(value, str):
        return None

    try:
        parsed = urlparse(value.strip())
        if parsed.scheme == "https" and parsed.hostname:
            return value.strip()
    except ValueError:
        pass

    return None


def recommend_stays(
    *,
    destinations: list[str],
    start_date: date,
    end_date: date,
    traveller_count: int,
    travel_style: str,
    total_budget: int,
) -> dict:
    """Research and rank accommodation candidates for a Karnataka trip."""

    if not destinations:
        raise ValueError("At least one destination is required.")

    if end_date < start_date:
        raise ValueError("End date cannot precede start date.")

    if traveller_count < 1 or total_budget < 1:
        raise ValueError("Traveller count and budget must be positive.")

    if travel_style not in ALLOWED_STYLES:
        raise ValueError("Unsupported travel style.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    duration_days = (end_date - start_date).days + 1
    nights = max(duration_days - 1, 1)

    # Planning allocation, not a verified accommodation quote.
    accommodation_share = {
        "budget": 0.30,
        "comfortable": 0.35,
        "premium": 0.40,
        "ultra-premium": 0.50,
    }[travel_style]

    accommodation_budget = round(total_budget * accommodation_share)

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are the accommodation research assistant for NammaPrayana,
a Karnataka tourism application.

Use Google Search to research real hotels, homestays, resorts or guesthouses.
Recommend at most four properties that best fit this trip.

TRIP
Destinations in route order: {json.dumps(destinations)}
Check-in: {start_date.isoformat()}
Check-out: {end_date.isoformat()}
Calendar days: {duration_days}
Nights: {nights}
Travellers: {traveller_count}
Travel style: {travel_style}
Total trip budget for the entire group: INR {total_budget}
Estimated accommodation allocation: INR {accommodation_budget}

BUDGET RULES
- The total budget must also cover transport, food, sightseeing and contingency.
- Accommodation allocation is only a planning estimate.
- Consider destination, group size, trip dates and travel style.
- Distinguish nightly rates from total-stay prices.
- Do not claim availability or booking confirmation.

EVIDENCE RULES
- Research actual properties using Google Search.
- Do not invent property names, prices, ratings, amenities, phone numbers or URLs.
- If a field cannot be supported by search evidence, return null or an empty list.
- Do not label a price as verified unless the source explicitly supports it.
- Provide source URLs actually found during research.
- A source URL is not automatically a booking URL.
- Include a booking URL only if a relevant property listing page was found.
- Ratings must include their source when available.
- Clearly explain why each property fits this trip.
- Return only valid JSON, with no Markdown fences.

Use this exact structure:
{{
  "budget_summary": {{
    "total_trip_budget_inr": {total_budget},
    "estimated_accommodation_budget_inr": {accommodation_budget},
    "budget_note": "Explain the estimated allocation and remaining trip expenses."
  }},
  "stays": [
    {{
      "name": "Property name",
      "destination": "Destination",
      "property_type": "Hotel, homestay, resort or guesthouse",
      "description": "Concise description",
      "estimated_price_inr": null,
      "price_period": "per_night, total_stay or not_verified",
      "rating": null,
      "rating_source": null,
      "amenities": [],
      "phone": null,
      "booking_url": null,
      "source_url": null,
      "why_recommended": "Suitability explanation",
      "price_status": "verified_listing_price or not_verified"
    }}
  ],
  "research_note": "Prices and availability may change."
}}

Return an empty stays list rather than fabricate properties.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ],
            
            temperature=0.2,
        ),
    )

    output = response.text
    if not output:
        raise RuntimeError("Gemini returned an empty stays response.")

    result = json.loads(output)

    if not isinstance(result, dict) or not isinstance(result.get("stays"), list):
        raise ValueError("Gemini returned an unexpected stays response.")

    cleaned_stays = []

    for stay in result["stays"][:4]:
        if not isinstance(stay, dict) or not stay.get("name"):
            continue

        price = stay.get("estimated_price_inr")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or price < 0
        ):
            price = None

        rating = stay.get("rating")
        if (
            isinstance(rating, bool)
            or not isinstance(rating, (int, float))
            or not 0 <= rating <= 5
        ):
            rating = None

        amenities = stay.get("amenities")
        if not isinstance(amenities, list):
            amenities = []

        phone = stay.get("phone")
        if not isinstance(phone, str) or not phone.strip():
            phone = None

        cleaned_stays.append({
            "name": str(stay["name"])[:160],
            "destination": str(
                stay.get("destination") or destinations[0]
            )[:100],
            "property_type": str(
                stay.get("property_type") or "Accommodation"
            )[:80],
            "description": str(stay.get("description") or "")[:500],
            "estimated_price_inr": price,
            "price_period": stay.get("price_period") or "not_verified",
            "rating": rating,
            "rating_source": stay.get("rating_source"),
            "amenities": [
                str(item)[:80] for item in amenities[:8]
            ],
            "phone": phone,
            "booking_url": _https_url(stay.get("booking_url")),
            "source_url": _https_url(stay.get("source_url")),
            "why_recommended": str(
                stay.get("why_recommended") or ""
            )[:500],
            "price_status": stay.get("price_status") or "not_verified",
        })

    result["stays"] = cleaned_stays

    budget_summary = result.get("budget_summary")
    if not isinstance(budget_summary, dict):
        budget_summary = {}

    budget_summary["total_trip_budget_inr"] = total_budget
    budget_summary["estimated_accommodation_budget_inr"] = accommodation_budget
    budget_summary.setdefault(
        "budget_note",
        "Accommodation allocation is an estimate; other trip expenses remain.",
    )

    result["budget_summary"] = budget_summary
    result.setdefault(
        "research_note",
        "Confirm prices, room occupancy and availability with the property.",
    )

    return result
