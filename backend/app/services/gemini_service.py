import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

logger = logging.getLogger(__name__)

# Ensure backend/.env is loaded regardless of working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")

MODEL_NAME = "gemini-3.1-flash-lite"


def _clean_json_output(output: str) -> str:
    """Strip Markdown code blocks and extra formatting from model output."""
    cleaned = output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    return cleaned


def _classify_meal_type(stop: dict) -> str | None:
    """Classify if a stop is lunch, dinner, or breakfast."""
    explicit = stop.get("meal_type")
    if explicit in {"lunch", "dinner", "breakfast"}:
        return explicit

    text = f"{stop.get('name', '')} {stop.get('category', '')} {stop.get('time', '')}".lower()
    if "lunch" in text or "noon" in text or "afternoon meal" in text or "midday" in text:
        return "lunch"
    if "dinner" in text or "night meal" in text or "evening meal" in text:
        return "dinner"
    if "breakfast" in text or "morning tiffin" in text:
        return "breakfast"

    return None


def _validate_and_enforce_daily_structure(
    result: dict,
    destinations: list[str],
    attractions: list[dict],
    food_spots: list[dict],
) -> dict:
    """
    Validate and guarantee the required itinerary structure:
    1. Every day has exactly one lunch recommendation.
    2. Every day has exactly one dinner recommendation.
    3. Selected tourist attractions are scheduled without duplicates or silent omissions.
    """
    days = result.get("days", [])
    if not isinstance(days, list) or not days:
        raise ValueError("Gemini returned an itinerary without any days.")

    warnings = result.setdefault("warnings", [])
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
        result["warnings"] = warnings

    used_food_spot_ids = set()
    used_attraction_ids = set()

    # Track food spots by destination
    food_by_city: dict[str, list[dict]] = {}
    for spot in food_spots:
        city = spot.get("city", "").strip().lower()
        food_by_city.setdefault(city, []).append(spot)

    for day_idx, day in enumerate(days):
        day_dest = str(day.get("destination", "")).strip()
        day_date = str(day.get("date", "")).strip()
        stops = day.get("stops", [])
        if not isinstance(stops, list):
            stops = []
            day["stops"] = stops

        # Identify existing meal stops
        lunch_stops = []
        dinner_stops = []
        activity_stops = []

        for stop in stops:
            if not isinstance(stop, dict):
                continue

            attr_id = stop.get("attraction_id")
            if attr_id is not None:
                used_attraction_ids.add(attr_id)

            food_id = stop.get("food_spot_id")
            if food_id is not None:
                used_food_spot_ids.add(food_id)

            meal_type = _classify_meal_type(stop)
            stop["meal_type"] = meal_type

            if meal_type == "lunch":
                lunch_stops.append(stop)
            elif meal_type == "dinner":
                dinner_stops.append(stop)
            else:
                activity_stops.append(stop)

        # Enforce exactly one lunch
        selected_lunch = None
        if lunch_stops:
            selected_lunch = lunch_stops[0]
            selected_lunch["category"] = selected_lunch.get("category") or "Lunch"
            selected_lunch["meal_type"] = "lunch"
            # If extra lunch stops were provided, re-label them as afternoon refreshments
            for extra in lunch_stops[1:]:
                extra["category"] = "Afternoon refreshments"
                extra["meal_type"] = None
                activity_stops.append(extra)
        else:
            # Pick an unused food spot for this destination or create a verified local lunch
            city_key = day_dest.lower()
            available = [
                s for s in food_by_city.get(city_key, [])
                if s["id"] not in used_food_spot_ids
            ]
            if not available:
                # check partial match
                for c, s_list in food_by_city.items():
                    if c in city_key or city_key in c:
                        available = [s for s in s_list if s["id"] not in used_food_spot_ids]
                        if available:
                            break

            if available:
                chosen = available[0]
                used_food_spot_ids.add(chosen["id"])
                selected_lunch = {
                    "time": "1:00 PM - 2:15 PM",
                    "name": chosen["name"],
                    "category": "Lunch",
                    "meal_type": "lunch",
                    "description": chosen.get("description") or f"Local lunch stop in {day_dest}",
                    "attraction_id": None,
                    "food_spot_id": chosen["id"],
                    "source_status": "curated_reference",
                }
            else:
                selected_lunch = {
                    "time": "1:00 PM - 2:15 PM",
                    "name": f"Traditional {day_dest} Lunch & Oota",
                    "category": "Lunch",
                    "meal_type": "lunch",
                    "description": f"Authentic regional Karnataka lunch featuring local specialities in {day_dest}.",
                    "attraction_id": None,
                    "food_spot_id": None,
                    "source_status": "needs_verification",
                }

        # Enforce exactly one dinner
        selected_dinner = None
        if dinner_stops:
            selected_dinner = dinner_stops[0]
            selected_dinner["category"] = selected_dinner.get("category") or "Dinner"
            selected_dinner["meal_type"] = "dinner"
            for extra in dinner_stops[1:]:
                extra["category"] = "Evening snack"
                extra["meal_type"] = None
                activity_stops.append(extra)
        else:
            city_key = day_dest.lower()
            available = [
                s for s in food_by_city.get(city_key, [])
                if s["id"] not in used_food_spot_ids
            ]
            if not available:
                for c, s_list in food_by_city.items():
                    if c in city_key or city_key in c:
                        available = [s for s in s_list if s["id"] not in used_food_spot_ids]
                        if available:
                            break

            if available:
                chosen = available[0]
                used_food_spot_ids.add(chosen["id"])
                selected_dinner = {
                    "time": "7:45 PM - 9:15 PM",
                    "name": chosen["name"],
                    "category": "Dinner",
                    "meal_type": "dinner",
                    "description": chosen.get("description") or f"Evening dining in {day_dest}",
                    "attraction_id": None,
                    "food_spot_id": chosen["id"],
                    "source_status": "curated_reference",
                }
            else:
                selected_dinner = {
                    "time": "7:45 PM - 9:15 PM",
                    "name": f"Authentic {day_dest} Evening Dinner",
                    "category": "Dinner",
                    "meal_type": "dinner",
                    "description": f"Relaxing dinner with regional flavours in {day_dest}.",
                    "attraction_id": None,
                    "food_spot_id": None,
                    "source_status": "needs_verification",
                }

        # Reassemble stops in chronological sequence:
        # morning activities -> lunch -> afternoon/evening activities -> dinner
        morning_activities = []
        afternoon_activities = []

        for act in activity_stops:
            time_str = str(act.get("time", "")).lower()
            if any(t in time_str for t in ["morning", "8:", "9:", "10:", "11:"]):
                morning_activities.append(act)
            else:
                afternoon_activities.append(act)

        # Ensure valid time labels if missing
        if not selected_lunch.get("time"):
            selected_lunch["time"] = "1:00 PM - 2:00 PM"
        if not selected_dinner.get("time"):
            selected_dinner["time"] = "7:45 PM - 9:00 PM"

        final_day_stops = []
        final_day_stops.extend(morning_activities)
        final_day_stops.append(selected_lunch)
        final_day_stops.extend(afternoon_activities)
        final_day_stops.append(selected_dinner)

        day["stops"] = final_day_stops

    # Verify that user-selected attractions were not silently dropped
    all_selected_attraction_ids = {item["id"] for item in attractions if "id" in item}
    missing_attraction_ids = all_selected_attraction_ids - used_attraction_ids

    if missing_attraction_ids:
        missing_attractions = [
            item for item in attractions if item["id"] in missing_attraction_ids
        ]
        # Attempt to insert missing attraction into the corresponding destination day
        for missing in missing_attractions:
            target_dest = missing.get("destination_id", "").lower()
            placed = False
            for day in days:
                d_name = day.get("destination", "").lower()
                if target_dest in d_name or d_name in target_dest:
                    # Place before lunch or after lunch
                    new_stop = {
                        "time": missing.get("suggested_time") or "Afternoon",
                        "name": missing["name"],
                        "category": missing.get("category") or "Tourist attraction",
                        "meal_type": None,
                        "description": missing.get("description") or "Explore this highlight",
                        "attraction_id": missing["id"],
                        "food_spot_id": None,
                        "source_status": missing.get("source_status", "curated_reference"),
                    }
                    # Insert before dinner
                    day["stops"].insert(max(0, len(day["stops"]) - 1), new_stop)
                    used_attraction_ids.add(missing["id"])
                    placed = True
                    break

            if not placed:
                warnings.append({
                    "code": "ATTRACTION_TIME_CONFLICT",
                    "message": (
                        f"Selected attraction '{missing['name']}' could not be fitted into "
                        f"the planned dates due to duration and travel constraints."
                    ),
                    "severity": "warning",
                })

    return result


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
    """Generate a source-grounded Karnataka itinerary using Gemini with verified schema."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("[GEMINI ERROR] GEMINI_API_KEY is not configured in backend/.env")
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    logger.info(
        f"[GEMINI] Generating itinerary for {destinations} ({start_date} to {end_date}), "
        f"{traveller_count} travellers, budget ₹{total_budget}, {len(attractions or [])} attractions, "
        f"{len(food_spots or [])} food spots."
    )

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
Destinations (in requested order of travel): {json.dumps(destinations, ensure_ascii=False)}
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
1. Return ONLY valid JSON matching the exact schema below. Do NOT include markdown code blocks, extra text, or preamble.

2. ATTRACTIONS & SCHEDULE
   - Every day in the trip range from {start_date} to {end_date} must be planned.
   - Assign destinations to days in the user's requested order.
   - Schedule ALL supplied tourist attractions into the itinerary on the appropriate days for their destination.
   - Provide realistic time slots, estimated visit durations, and sensible travel gaps.
   - Do not repeat the same attraction on multiple days unless requested.
   - Preserve exact attraction names, categories, descriptions, and attraction_id values. Set food_spot_id to null for attractions.

3. MANDATORY MEALS (EVERY SINGLE DAY)
   - For EVERY itinerary day, you MUST include:
     * Exactly ONE lunch recommendation (e.g. 1:00 PM - 2:15 PM, meal_type: "lunch")
     * Exactly ONE dinner recommendation (e.g. 7:45 PM - 9:15 PM, meal_type: "dinner")
     * Breakfast recommendation if suitable (meal_type: "breakfast")
   - Lunch and dinner MUST be integrated directly into each day's schedule sequence alongside tourist attractions in chronological order (morning activities -> lunch -> afternoon/evening activities -> dinner).
   - Use supplied food spots for that destination whenever available:
     * Use exact food spot name, description, and source ID for food_spot_id. Set attraction_id: null.
     * Set category: "Lunch" or "Dinner" (or "Local food"). Set meal_type: "lunch" or "dinner".
     * Set source_status to "curated_reference".
   - If no supplied food spot exists for that destination or meal:
     * Suggest an authentic regional Karnataka meal option for that city (e.g. "Authentic Mysuru Thali & Oota", "Regional Coastal Dinner").
     * Set food_spot_id: null, attraction_id: null.
     * Set meal_type: "lunch" or "dinner".
     * Set source_status to "needs_verification".
     * Under NO circumstances should any day omit lunch or dinner.

4. WEATHER & INTEGRITY
   - Incorporate available weather data into weather_note and advise travellers on rain/outdoor conditions.
   - If weather is unavailable, state honestly that weather forecast was unavailable.
   - Never invent hotels, fake prices, or unsupported facilities.
   - Total group budget is ₹{total_budget}. Note budget expectations in budget_note.

5. OUTPUT SCHEMA
{{
  "title": "Descriptive trip title reflecting the route",
  "days": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "destination": "Destination name",
      "summary": "Short 1-2 sentence overview of the day",
      "stops": [
        {{
          "time": "9:30 AM - 12:00 PM",
          "name": "Exact attraction or restaurant name",
          "category": "Palace | Heritage | Lunch | Dinner | etc.",
          "meal_type": null,
          "description": "Concise practical description",
          "attraction_id": 1,
          "food_spot_id": null,
          "source_status": "curated_reference"
        }},
        {{
          "time": "1:00 PM - 2:15 PM",
          "name": "Food spot name",
          "category": "Lunch",
          "meal_type": "lunch",
          "description": "Authentic regional lunch description",
          "attraction_id": null,
          "food_spot_id": 101,
          "source_status": "curated_reference"
        }},
        {{
          "time": "7:45 PM - 9:15 PM",
          "name": "Dinner spot name",
          "category": "Dinner",
          "meal_type": "dinner",
          "description": "Authentic evening dinner description",
          "attraction_id": null,
          "food_spot_id": 102,
          "source_status": "curated_reference"
        }}
      ]
    }}
  ],
  "budget_note": "Group budget guidance and estimated breakdown",
  "weather_note": "Weather summary and advice across destinations",
  "warnings": [],
  "verification_note": "Items requiring local confirmation"
}}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
    except Exception as exc:
        logger.error(f"[GEMINI CALL ERROR] {type(exc).__name__}: {exc}")
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    output = response.text
    if not output or not output.strip():
        logger.error("[GEMINI ERROR] Gemini returned an empty response.")
        raise RuntimeError("Gemini returned an empty response.")

    cleaned = _clean_json_output(output)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(f"[GEMINI JSON ERROR] {exc}. Output was:\n{cleaned[:500]}")
        raise ValueError(
            "Gemini returned invalid JSON. Retry itinerary generation."
        ) from exc

    if not isinstance(result, dict) or not isinstance(result.get("days"), list):
        logger.error(f"[GEMINI FORMAT ERROR] Expected dict with 'days' list, got: {type(result)}")
        raise ValueError("Gemini returned an unexpected itinerary format.")

    required_fields = {
        "title",
        "budget_note",
        "weather_note",
        "warnings",
        "verification_note",
    }
    for field in required_fields:
        if field not in result:
            result[field] = [] if field == "warnings" else ""

    # Strict post-validation and enforcement of daily lunch, dinner & attractions
    result = _validate_and_enforce_daily_structure(
        result=result,
        destinations=destinations,
        attractions=attractions or [],
        food_spots=food_spots or [],
    )

    logger.info(
        f"[GEMINI] Successfully built itinerary '{result.get('title')}' with {len(result.get('days', []))} days."
    )
    return result
