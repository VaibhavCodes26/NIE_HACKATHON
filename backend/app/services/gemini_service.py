
import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"


def generate_itinerary(
    *,
    destinations: list[str],
    start_date: str,
    end_date: str,
    traveller_count: int,
    travel_style: str,
    total_budget: int,
    interests: list[str],
    attractions: list[dict] | None = None,
    food_spots: list[dict] | None = None,
    weather_data: list[dict] | None = None,
    adjustment_request: str = "",
) -> dict:
    """Generate a source-grounded Karnataka itinerary using Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    source_data = {
        "attractions": attractions or [],
        "food_spots": food_spots or [],
        "weather": weather_data or [],
    }
    adjustment_section = (
        f"""
USER REQUESTED PERSONALISATION
{adjustment_request.strip()}

Apply these preferences wherever feasible. Adjust activity intensity, rest
breaks, and scheduling for the stated travel pace, senior citizens, children,
pregnancy, accessibility needs, strenuous treks, exposed activities, and
custom notes. Never invent facilities or accessibility claims. Do not override
source integrity, safety, dates, selected attractions, or budget. Explain
unmet preferences in warnings.
"""
        if adjustment_request and adjustment_request.strip()
        else "No additional personalisation requested."
    )

   
    prompt = f"""
You are NammaPrayana, a practical Karnataka travel-planning AI.

TRIP
Destinations: {json.dumps(destinations, ensure_ascii=False)}
Dates: {start_date} to {end_date}
Travellers: {traveller_count}
Travel style: {travel_style}
Total group budget (INR): {total_budget}
Interests: {json.dumps(interests, ensure_ascii=False)}

PERSONALISATION
{adjustment_section}

VERIFIED INPUT RECORDS
{json.dumps(source_data, ensure_ascii=False, separators=(",", ":"))}

RULES
1. Return only valid JSON matching the exact schema below. No Markdown or
   extra text.

2. Use only supplied attraction, food, and weather records. Preserve exact
   source names, IDs, categories, descriptions, and source_status values.
   Never invent records, IDs, metadata, dishes, locations, facilities,
   opening hours, ratings, prices, bookings, or transport schedules.

3. Include every selected attraction present in the supplied data. If dates,
   time, weather, or feasibility prevent this, explain the limitation in
   warnings; never silently omit selected attractions.

4. Cover every requested date and destination in sensible order. Balance
   activities, meals, rest, and travel buffers. Keep each day realistic;
   do not invent travel times or schedules.

5. MEALS
   - Include lunch and dinner on each full travel day when suitable supplied
     food records exist for that destination.
   - Include breakfast only when a suitable record exists.
   - Use exact food spot names, IDs, and descriptions.
   - Avoid repeating food spots unless necessary.
   - Never invent a meal option; mention unavailable options in warnings.

6. SOURCE INTEGRITY
   - Attraction stops must use exact attraction names, categories,
     descriptions, and IDs.
   - Food stops must use exact food spot names, IDs, and descriptions.
   - Attraction stops: attraction_id = source ID, food_spot_id = null.
   - Food stops: food_spot_id = source ID, attraction_id = null.
   - Never use attraction categories for restaurants or infer unsupported
     location, proximity, ownership, history, or speciality dishes.
   - If a food category is unavailable, use "Food stop".
   - Use source_status from the source; otherwise use
     "needs_verification". Never invent missing IDs.

7. WEATHER
   Use only supplied weather records matched to destination and date. If
   weather is unavailable, say it was not checked. For thunderstorms, heavy
   rain, or high rain probability, warn travellers and prefer suitable
   supplied indoor attractions where supported. Never claim an attraction
   is indoors without evidence.

8. BUDGET
   Treat total_budget as the entire group's budget. Label costs as estimates
   and warn if the itinerary may exceed budget. Do not invent confirmed costs.

9. PERSONALISATION
   Apply the user's stated preferences where feasible, including travel pace,
   senior citizens, children, pregnancy, accessibility, strenuous treks,
   exposed activities, and custom notes. Adjust activity intensity, rest
   breaks, and scheduling accordingly. Never claim unsupported accessibility
   or facilities. Preferences must not override source integrity, safety,
   dates, selected attractions, or budget. Explain unmet preferences in
   warnings.

10. Keep descriptions concise. Accommodation is outside this response's
    scope; do not invent hotels. Include useful warnings about missing meal
    options, missing weather data, scheduling limitations, budget, and
    details requiring verification.

Return exactly this JSON structure:
{{
  "title": "Trip title",
  "days": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "destination": "Destination name",
      "stops": [
        {{
          "time": "Morning",
          "name": "Exact source name",
          "category": "Source category",
          "description": "Short practical description",
          "attraction_id": 1,
          "food_spot_id": null,
          "source_status": "needs_verification"
        }}
      ]
    }}
  ],
  "budget_note": "Group budget estimate and limitations",
  "weather_note": "Forecast summary or not checked",
  "warnings": [],
  "verification_note": "Details requiring verification"
}}

Every day must include day_number, date, destination, and stops. Every stop
must include time, name, category, description, attraction_id, food_spot_id,
and source_status. Preserve the exact source ID for the applicable stop type;
use null for the other ID. Do not invent missing IDs or extra schema fields.
"""


    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
    )

    output = interaction.output_text
    if not output or not output.strip():
        raise RuntimeError("Gemini returned an empty response.")

    cleaned = output.strip()

    # Handle JSON accidentally wrapped in Markdown fences.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Gemini returned invalid JSON. Retry itinerary generation."
        ) from exc

    if not isinstance(result, dict) or not isinstance(result.get("days"), list):
        raise ValueError("Gemini returned an unexpected itinerary format.")

    required_fields = {
        "title",
        "budget_note",
        "weather_note",
        "warnings",
        "verification_note",
    }
    missing_fields = required_fields - result.keys()
    if missing_fields:
        raise ValueError(
            f"Gemini response is missing fields: {', '.join(sorted(missing_fields))}"
        )

    return result
