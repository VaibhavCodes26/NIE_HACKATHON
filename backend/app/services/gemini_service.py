import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai

from app.services import gati_service

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
    gati_plan: Optional[dict] = None,
    selected_attraction_ids: Optional[list[int]] = None,
) -> dict:
    """
    Validate and guarantee the required itinerary structure:
    1. Every day has exactly one lunch recommendation.
    2. Every day has exactly one dinner recommendation.
    3. Gati schedule is the single authoritative source of truth:
       - No moved attractions.
       - No duplicated attractions.
       - Missing scheduled attractions recovered on their assigned day.
       - Deferred attractions strictly excluded from daily stops.
    """
    days = result.get("days", [])
    if not isinstance(days, list) or not days:
        raise ValueError("Gemini returned an itinerary without any days.")

    warnings = result.setdefault("warnings", [])
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
        result["warnings"] = warnings

    # Food spots by city
    used_food_spot_ids = set()
    food_by_city: dict[str, list[dict]] = {}
    for spot in food_spots:
        city = str(spot.get("city", "")).strip().lower()
        food_by_city.setdefault(city, []).append(spot)

    # If gati_plan is provided, establish authoritative day allocation
    gati_days = gati_plan.get("days", []) if gati_plan else []
    assigned_day_by_id: dict[int | str, int] = {}
    gati_stop_by_id: dict[int | str, dict] = {}
    scheduled_ids_by_day: dict[int, list[int | str]] = {}
    deferred_ids: set[int | str] = set()

    if gati_plan:
        for gd in gati_days:
            d_num = gd.get("day") or gd.get("day_number", 1)
            scheduled_ids_by_day[d_num] = []
            for s in gd.get("stops", []):
                s_id = s.get("id")
                if s_id is not None:
                    assigned_day_by_id[s_id] = d_num
                    gati_stop_by_id[s_id] = s
                    scheduled_ids_by_day[d_num].append(s_id)

        for d_item in gati_plan.get("deferred", []):
            if d_item.get("id") is not None:
                deferred_ids.add(d_item["id"])

    # Ensure result has days matching gati_days if gati_days exists
    if gati_days and len(days) < len(gati_days):
        for missing_idx in range(len(days), len(gati_days)):
            gd_template = gati_days[missing_idx]
            days.append({
                "day_number": missing_idx + 1,
                "date": gd_template.get("date", ""),
                "destination": gd_template.get("destination", destinations[-1] if destinations else "Karnataka"),
                "summary": "Flexible exploration and leisure.",
                "stops": [],
            })

    # Track which attraction IDs have been scheduled
    globally_placed_attractions = set()

    for day_idx, day in enumerate(days):
        d_num = day_idx + 1
        day["day_number"] = d_num

        gd = gati_days[day_idx] if day_idx < len(gati_days) else None
        if gd:
            day["destination"] = gd.get("destination") or day.get("destination", "")
            if gd.get("cities"):
                day["cities"] = gd["cities"]
            if gd.get("date"):
                day["date"] = gd["date"]
            day["effort_total"] = gd.get("total", 0)
            day["capacity"] = gd.get("capacity", gati_plan.get("summary", {}).get("capacity", 110))
            day["status"] = gd.get("status", "ok")
            day["notes"] = gd.get("notes", [])

        day_dest = str(day.get("destination", "")).strip()
        raw_stops = day.get("stops", [])
        if not isinstance(raw_stops, list):
            raw_stops = []

        breakfast_stops = []
        lunch_stops = []
        dinner_stops = []
        activity_stops = []

        day_scheduled_ids = set()

        for stop in raw_stops:
            if not isinstance(stop, dict):
                continue

            attr_id = stop.get("attraction_id")
            food_id = stop.get("food_spot_id")
            meal_type = _classify_meal_type(stop)
            stop["meal_type"] = meal_type

            if meal_type == "breakfast":
                breakfast_stops.append(stop)
                continue
            if meal_type == "lunch":
                lunch_stops.append(stop)
                if food_id is not None:
                    used_food_spot_ids.add(food_id)
                continue
            if meal_type == "dinner":
                dinner_stops.append(stop)
                if food_id is not None:
                    used_food_spot_ids.add(food_id)
                continue

            # Attempt to resolve attraction_id by name if not explicitly set
            if attr_id is None and not food_id and meal_type is None:
                stop_name_clean = str(stop.get("name", "")).strip().lower()
                for gid, gst in gati_stop_by_id.items():
                    gname = str(gst.get("name", "")).strip().lower()
                    if stop_name_clean and (stop_name_clean == gname or stop_name_clean in gname or gname in stop_name_clean):
                        attr_id = gid
                        stop["attraction_id"] = gid
                        break

            # It's an attraction/activity stop
            if attr_id is not None:
                # If Gati explicitly deferred it, do NOT include in day schedule!
                if attr_id in deferred_ids:
                    continue

                # If Gati assigned it to a different day, omit here (will be restored on correct day)
                if assigned_day_by_id and assigned_day_by_id.get(attr_id) != d_num:
                    continue

                # Prevent duplicates
                if attr_id in day_scheduled_ids or attr_id in globally_placed_attractions:
                    continue

                day_scheduled_ids.add(attr_id)
                globally_placed_attractions.add(attr_id)

                if attr_id in gati_stop_by_id:
                    gst = gati_stop_by_id[attr_id]
                    stop["effort"] = gst.get("effort")
                    stop["level"] = gst.get("level")
                    if gst.get("safety_flag"):
                        stop["safety_flag"] = gst["safety_flag"]
                    if gst.get("safety_note"):
                        stop["safety_note"] = gst["safety_note"]
                    if gst.get("accessibility_flag"):
                        stop["accessibility_flag"] = gst["accessibility_flag"]
                    if gst.get("accessibility_note"):
                        stop["accessibility_note"] = gst["accessibility_note"]
                    if gst.get("weather_note"):
                        stop["weather_note"] = gst["weather_note"]
                    if gst.get("is_mandatory") is not None:
                        stop["is_mandatory"] = gst["is_mandatory"]
                    if not stop.get("category"):
                        stop["category"] = gst.get("category", "Tourist attraction")

            activity_stops.append(stop)

        # Recover missing Gati scheduled attractions for this specific day
        if gati_plan and d_num in scheduled_ids_by_day:
            for required_id in scheduled_ids_by_day[d_num]:
                if required_id not in day_scheduled_ids:
                    gstop = gati_stop_by_id.get(required_id, {})
                    recovered = {
                        "time": gstop.get("suggested_time") or ("Morning" if len(activity_stops) < 2 else "Afternoon"),
                        "name": gstop.get("name", "Attraction"),
                        "category": gstop.get("category") or "Tourist attraction",
                        "meal_type": None,
                        "description": gstop.get("description") or f"Explore {gstop.get('name', 'this highlight')}.",
                        "attraction_id": required_id,
                        "food_spot_id": None,
                        "source_status": gstop.get("source_status", "curated_reference"),
                        "effort": gstop.get("effort"),
                        "level": gstop.get("level"),
                        "safety_flag": gstop.get("safety_flag"),
                        "safety_note": gstop.get("safety_note"),
                        "accessibility_flag": gstop.get("accessibility_flag"),
                        "accessibility_note": gstop.get("accessibility_note"),
                        "weather_note": gstop.get("weather_note"),
                        "is_mandatory": gstop.get("is_mandatory"),
                    }
                    activity_stops.append(recovered)
                    day_scheduled_ids.add(required_id)
                    globally_placed_attractions.add(required_id)

        # Enforce exactly one lunch
        selected_lunch = None
        if lunch_stops:
            selected_lunch = lunch_stops[0]
            selected_lunch["category"] = selected_lunch.get("category") or "Lunch"
            selected_lunch["meal_type"] = "lunch"
            for extra in lunch_stops[1:]:
                extra["category"] = "Afternoon refreshments"
                extra["meal_type"] = None
                activity_stops.append(extra)
        else:
            city_key = day_dest.lower()
            available = [s for s in food_by_city.get(city_key, []) if s["id"] not in used_food_spot_ids]
            if not available:
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
                    "name": f"Traditional {day_dest or 'Karnataka'} Lunch & Oota",
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
            available = [s for s in food_by_city.get(city_key, []) if s["id"] not in used_food_spot_ids]
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
                    "name": f"Authentic {day_dest or 'Karnataka'} Evening Dinner",
                    "category": "Dinner",
                    "meal_type": "dinner",
                    "description": f"Relaxing dinner with regional flavours in {day_dest}.",
                    "attraction_id": None,
                    "food_spot_id": None,
                    "source_status": "needs_verification",
                }

        # Chronological sequence: morning -> lunch -> afternoon/evening -> dinner
        morning_activities = []
        afternoon_activities = []

        for act in activity_stops:
            time_str = str(act.get("time", "")).lower()
            if any(t in time_str for t in ["morning", "8:", "9:", "10:", "11:"]):
                morning_activities.append(act)
            elif any(t in time_str for t in ["afternoon", "evening", "12:", "1:", "2:", "3:", "4:", "5:", "6:"]):
                afternoon_activities.append(act)
            else:
                # Distribute evenly if time slot not specified
                if len(morning_activities) <= len(afternoon_activities):
                    morning_activities.append(act)
                else:
                    afternoon_activities.append(act)

        if not selected_lunch.get("time"):
            selected_lunch["time"] = "1:00 PM - 2:00 PM"
        if not selected_dinner.get("time"):
            selected_dinner["time"] = "7:45 PM - 9:00 PM"

        final_day_stops = []
        if breakfast_stops:
            final_day_stops.append(breakfast_stops[0])
        final_day_stops.extend(morning_activities)
        final_day_stops.append(selected_lunch)
        final_day_stops.extend(afternoon_activities)
        final_day_stops.append(selected_dinner)

        day["stops"] = final_day_stops

    # Attach Gati plan, deferred items, unscheduled items, and warnings
    if gati_plan:
        result["gati"] = gati_plan
        result["deferred"] = gati_plan.get("deferred", [])
        result["unscheduled"] = gati_plan.get("deferred", [])
        for w in gati_plan.get("warnings", []):
            if w not in result["warnings"]:
                result["warnings"].append(w)

    # Final Integrity Check: ensure every feasible selected attraction appears in the schedule
    if selected_attraction_ids:
        all_scheduled_ids = set()
        for d in days:
            for s in d.get("stops", []):
                sid = s.get("attraction_id")
                if sid is not None:
                    all_scheduled_ids.add(int(sid))

        deferred_ids_all = {int(x["id"]) for x in result.get("deferred", []) if x.get("id") is not None}

        for req_id in selected_attraction_ids:
            req_id_int = int(req_id)
            if req_id_int not in all_scheduled_ids and req_id_int not in deferred_ids_all:
                matched_attr = next((a for a in (attractions or []) if int(a.get("id", -1)) == req_id_int), None)
                if matched_attr:
                    target_day = days[0]
                    attr_city = str(matched_attr.get("city") or matched_attr.get("destination_id") or "").lower()
                    for d in days:
                        d_dest = str(d.get("destination", "")).lower()
                        if attr_city and (attr_city in d_dest or d_dest in attr_city):
                            target_day = d
                            break
                    target_day["stops"].insert(-1 if len(target_day["stops"]) > 1 else len(target_day["stops"]), {
                        "time": matched_attr.get("suggested_time") or "Morning",
                        "name": matched_attr.get("name", "Attraction"),
                        "category": matched_attr.get("category") or "Tourist attraction",
                        "meal_type": None,
                        "description": matched_attr.get("description") or f"Explore {matched_attr.get('name')}.",
                        "attraction_id": req_id_int,
                        "food_spot_id": None,
                        "source_status": matched_attr.get("source_status", "curated_reference"),
                        "effort": matched_attr.get("effort") or 30,
                        "level": "low" if (matched_attr.get("effort") or 30) < 25 else "medium",
                        "is_mandatory": True,
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
    gati_plan: dict | None = None,
    selected_attraction_ids: list[int] | None = None,
) -> dict:
    """Generate a source-grounded Karnataka itinerary using Gemini with verified schema and Gati pacing."""

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

    gati_prompt_section = ""
    if gati_plan:
        gati_prompt_section = f"""
NAMMA GATI PACING SCHEDULE (AUTHORITATIVE):
{gati_service.to_prompt(gati_plan)}

CRITICAL NAMMA GATI INSTRUCTIONS:
1. The pacing engine has ALREADY scheduled the tourist attractions for each day.
2. Follow this schedule strictly. Do NOT add, remove, or swap attractions between days.
3. Every scheduled attraction MUST appear on its designated day with its exact attraction_id and name.
4. If an attraction is marked as deferred / left out, do NOT schedule it on any day.
5. Weave realistic timings, rest pauses, and visit descriptions around this fixed allocation.
"""

    adjustment_section = (
        f"""
USER REQUESTED PERSONALISATION
{adjustment_request.strip()}

Apply these preferences wherever feasible without violating the fixed Namma Gati schedule.
Adjust activity pacing, rest breaks, and descriptions accordingly.
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

{gati_prompt_section}

PERSONALISATION
{adjustment_section}

VERIFIED INPUT RECORDS
{json.dumps(source_data, ensure_ascii=False, separators=(",", ":"))}

RULES
1. Return ONLY valid JSON matching the exact schema below. Do NOT include markdown code blocks, extra text, or preamble.

2. ATTRACTIONS & SCHEDULE
   - Every day in the trip range from {start_date} to {end_date} must be planned.
   - Strictly follow the Namma Gati allocation. Keep each attraction on its designated day.
   - Provide realistic time slots, estimated visit durations, and sensible travel gaps.
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

    # Strict post-validation and enforcement of daily lunch, dinner & authoritative Gati schedule
    result = _validate_and_enforce_daily_structure(
        result=result,
        destinations=destinations,
        attractions=attractions or [],
        food_spots=food_spots or [],
        gati_plan=gati_plan,
        selected_attraction_ids=selected_attraction_ids,
    )

    logger.info(
        f"[GEMINI] Successfully built itinerary '{result.get('title')}' with {len(result.get('days', []))} days."
    )
    return result
