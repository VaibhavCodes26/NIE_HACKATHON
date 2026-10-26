"""
Namma Gati: stamina-aware pacing for itineraries.

Pure Python. No external API calls, no tokens. Runs BEFORE Gemini:
    selected attractions -> effort score each -> fit into days under a per-day
    stamina budget (lower for seniors / pregnancy / children / mobility needs)
    -> Gemini only narrates the fixed plan (adds meals, timings, descriptions).

The effort numbers are editorial ratings (our own estimates), not measurements.
Tune RULES / EFFORT_OVERRIDES freely, or store an `effort` (0-100) column in your DB.
"""
import re
from datetime import date, timedelta
from typing import Any, Optional

BASE_CAPACITY = 150      # effort points a healthy adult group can handle per day
CITY_CHANGE_COST = 40    # extra effort if a day covers two cities (travel between them)
STRETCH = 1.15           # a day may go 15% over capacity before a stop is deferred

# (regex, points). The highest matching rule wins.
RULES = [
    (r"trek|hike|climb|summit|peak|rappel|rafting|adventure|zip", 70),
    (r"steps|stairs", 60),
    (r"\bhill|betta|giri|ghat|mountain", 55),
    (r"waterfall|\bfalls\b", 50),
    (r"\bfort\b|kote", 45),
    (r"cave|gufa", 45),
    (r"safari|wildlife|sanctuary|national park|elephant camp", 40),
    (r"heritage|monument|ruins|archaeolog|temple complex", 35),
    (r"palace|mahal", 30),
    (r"temple|mandir|basadi|basti|church|mosque|masjid|gurudwara|matha|devasthana", 25),
    (r"market|bazaar|bazar|shopping|mall|emporium", 25),
    (r"beach|island|backwater|boating|coracle", 25),
    (r"museum|gallery|planetarium|science", 20),
    (r"park|garden|lake|dam|zoo|aquarium|botanical", 20),
    (r"viewpoint|view point|sunset|sunrise|\bpoint\b|spa|cafe|café|resort|food street|darshini", 15),
]
DEFAULT_EFFORT = 30

# Known strenuous places (matched against the lower-cased name).
EFFORT_OVERRIDES = {
    "shravanabelagola": 75,
    "kudremukh": 85,
    "mullayanagiri": 70,
    "tadiandamol": 85,
    "skandagiri": 85,
    "savandurga": 80,
    "kumaraparvatha": 90,
    "kumara parvatha": 90,
    "kodachadri": 80,
}

_LAST_WORDS = re.compile(r"sunset|sunrise|viewpoint|view point|\bpoint\b")
_STRENUOUS_RX = re.compile(r"trek|hike|climb|summit|peak|rappel|rafting|adventure|zip")
_INDOOR_RX = re.compile(r"museum|gallery|planetarium|science centre|science museum|aquarium|palace|mahal|temple|church|mosque|masjid|art gallery|heritage museum|indoor")
_OUTDOOR_RX = re.compile(r"trek|hike|peak|hill|betta|giri|waterfall|falls|beach|lake|viewpoint|garden|park|safari|sanctuary|ruins|dam|coracle|adventure")
_STAIRS_RX = re.compile(r"steps|stairs|hill|betta|giri|fort|kote|cave|gufa|ruins|rocks|monolith")


def _text(a: dict, keys) -> str:
    parts = []
    for k in keys:
        v = a.get(k)
        if isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        elif v:
            parts.append(str(v))
    return " ".join(parts).lower()


def effort_of(a: dict) -> int:
    """
    Effort 0-100 for one attraction dict.
    Supports duration in either estimated_duration_minutes or duration_hours.
    Explicit effort is validated and clamped between 0 and 100.
    """
    explicit = a.get("effort")
    if isinstance(explicit, (int, float)):
        return int(max(0, min(100, round(explicit))))

    name = str(a.get("name", "")).lower()
    for key, pts in EFFORT_OVERRIDES.items():
        if key in name:
            return pts

    pts = 0
    for source in (("name", "category", "type", "tags", "interest_tags"), ("description",)):
        blob = _text(a, source)
        hits = [p for rx, p in RULES if re.search(rx, blob)]
        if hits:
            pts = max(hits)
            break
    if not pts:
        pts = DEFAULT_EFFORT

    # Duration handling: check duration_hours or estimated_duration_minutes
    hours = a.get("duration_hours")
    if hours is None and a.get("estimated_duration_minutes") is not None:
        try:
            hours = float(a["estimated_duration_minutes"]) / 60.0
        except (ValueError, TypeError):
            hours = None

    if isinstance(hours, (int, float)) and hours > 2:
        pts += min(15, int((hours - 2) * 5))

    return int(max(0, min(100, pts)))


def level_of(e: int) -> str:
    return "low" if e < 25 else "medium" if e < 50 else "high"


def capacity(profile: Optional[dict] = None, pace: str = "balanced") -> int:
    """The weakest traveller sets the pace for the whole group."""
    p = profile or {}
    mult = [1.0]
    if p.get("senior"):
        mult.append(0.70)
    if p.get("pregnant"):
        mult.append(0.60)
    if p.get("child"):
        mult.append(0.80)
    if p.get("mobility"):
        mult.append(0.55)
    if p.get("less_walking") or p.get("less-walking"):
        mult.append(0.75)
    if p.get("easy_pace") or p.get("easy-pace"):
        mult.append(0.75)

    pace_key = str(pace or "balanced").strip().lower()
    pace_m = {
        "relaxed": 0.8,
        "less-walking": 0.8,
        "easy-pace": 0.8,
        "balanced": 1.0,
        "packed": 1.2,
        "fast": 1.2,
    }.get(pace_key, 1.0)

    return int(round(BASE_CAPACITY * min(mult) * pace_m))


def _paced_for(profile: Optional[dict]) -> list[str]:
    p = profile or {}
    names = {
        "senior": "senior citizens",
        "pregnant": "pregnancy",
        "child": "young children",
        "mobility": "limited mobility",
        "avoid_strenuous": "avoiding strenuous treks",
        "less_walking": "less walking",
        "easy_pace": "easy pace",
        "rain_friendly": "rain-friendly options",
    }
    return [v for k, v in names.items() if p.get(k)]


def _order_day(stops: list) -> list:
    """Hardest first (cooler in the morning); sunset / viewpoint stops last."""
    return sorted(
        stops,
        key=lambda s: (1 if _LAST_WORDS.search(str(s.get("name", "")).lower()) else 0, -s.get("effort", 0)),
    )


def _resolve_city(a: dict, city_order: list[str]) -> str:
    """Resolve the attraction's city, matching against city_order to prevent 'Trip' defaults."""
    raw = str(a.get("city") or a.get("destination_name") or a.get("destination_id") or "").strip()
    if not raw:
        return city_order[0] if city_order else "Trip"

    raw_clean = raw.lower().replace("-", " ")
    for c in city_order:
        c_clean = c.lower().replace("-", " ")
        if raw_clean == c_clean or raw_clean in c_clean or c_clean in raw_clean:
            return c

    return raw


def _is_strenuous(a: dict, effort: int) -> bool:
    if effort >= 60:
        return True
    blob = _text(a, ("name", "category", "tags", "interest_tags", "description"))
    return bool(_STRENUOUS_RX.search(blob))


def _is_indoor(a: dict) -> bool:
    blob = _text(a, ("name", "category", "tags", "interest_tags", "description"))
    return bool(_INDOOR_RX.search(blob))


def _has_stairs(a: dict) -> bool:
    blob = _text(a, ("name", "category", "tags", "interest_tags", "description"))
    return bool(_STAIRS_RX.search(blob))


def plan(
    stops: list,
    n_days: int,
    profile: Optional[dict] = None,
    cities: Optional[list] = None,
    pace: str = "balanced",
    start_date: Optional[Any] = None,
    selected_attraction_ids: Optional[list[int]] = None,
    weather_data: Optional[list[dict]] = None,
) -> dict:
    """
    Deterministic stamina-aware itinerary allocator.
    Prioritizes mandatory user selections first, applies traveller comfort/safety
    constraints, and schedules realistically across n_days.
    """
    n_days = max(1, int(n_days or 1))
    p = profile or {}

    senior = bool(p.get("senior"))
    pregnant = bool(p.get("pregnant"))
    mobility = bool(p.get("mobility"))
    child = bool(p.get("child"))
    avoid_strenuous = bool(p.get("avoid_strenuous"))
    less_walking = bool(p.get("less_walking") or p.get("less-walking") or pace == "less-walking")
    easy_pace = bool(p.get("easy_pace") or p.get("easy-pace") or pace == "easy-pace")
    rain_friendly = bool(p.get("rain_friendly") or pace == "rain-friendly")

    effective_pace = "relaxed" if (less_walking or easy_pace or pace in {"relaxed", "less-walking", "easy-pace"}) else pace

    cap = capacity(p, effective_pace)
    max_stops = max(2, min(5, round(cap / 22)))
    if senior or less_walking or easy_pace or mobility:
        max_stops = min(max_stops, 3)

    single_limit = round(cap * 0.8)

    # Clean and order requested cities
    order: list[str] = []
    for c in (cities or []):
        c_str = str(c).strip()
        if c_str and c_str not in order:
            order.append(c_str)

    # Selected IDs set
    selected_id_set = {int(x) for x in selected_attraction_ids} if selected_attraction_ids else set()

    # Process and deduplicate stops
    seen_ids = set()
    mandatory_items = []
    optional_items = []
    deferred = []

    for a in stops:
        stop_id = a.get("id")
        if stop_id is not None:
            if stop_id in seen_ids:
                continue
            seen_ids.add(stop_id)

        e = effort_of(a)
        city = _resolve_city(a, order)

        if city and city not in order and city != "Trip":
            order.append(city)

        is_mandatory = (int(stop_id) in selected_id_set) if selected_id_set else True
        is_must_visit = bool(a.get("is_must_visit"))

        it = {
            "id": stop_id,
            "name": str(a.get("name", "Unnamed place")),
            "city": city,
            "category": a.get("category") or "Tourist attraction",
            "description": a.get("description") or "",
            "suggested_time": a.get("suggested_time") or "",
            "source_status": a.get("source_status") or "needs_verification",
            "effort": e,
            "level": level_of(e),
            "is_mandatory": is_mandatory,
            "is_must_visit": is_must_visit,
            "visit_order": a.get("visit_order", 999),
            "estimated_duration_minutes": a.get("estimated_duration_minutes") or 90,
            "safety_flag": None,
            "safety_note": None,
            "accessibility_flag": None,
            "accessibility_note": None,
            "weather_note": None,
        }

        strenuous = _is_strenuous(a, e)
        indoor = _is_indoor(a)
        has_stairs_val = _has_stairs(a)

        # -------------------------------------------------------------
        # Hard Safety & Physical Constraints
        # -------------------------------------------------------------
        if avoid_strenuous and strenuous:
            deferred.append({
                **it,
                "code": "avoid_strenuous",
                "reason": "Excluded from daily schedule because 'Avoid strenuous treks' preference is active.",
            })
            continue

        if pregnant and (strenuous or e >= 65):
            deferred.append({
                **it,
                "code": "unsuitable_pregnancy",
                "reason": "Excluded for safety: Activity involves strenuous trekking, steep climbing, or high physical exertion unsuitable during pregnancy.",
            })
            continue

        if senior and e > single_limit:
            deferred.append({
                **it,
                "code": "strenuous",
                "reason": f"Too strenuous for this group (effort {e}, comfortable limit {single_limit}).",
            })
            continue

        if mobility and (strenuous or e >= 65):
            deferred.append({
                **it,
                "code": "strenuous",
                "reason": f"Inaccessible or too strenuous for mobility limitations (effort {e}).",
            })
            continue

        # -------------------------------------------------------------
        # Soft Preference Flags (Preserve attraction, attach transparent advisory)
        # -------------------------------------------------------------
        if pregnant and (has_stairs_val or e >= 40):
            it["safety_flag"] = "suitability_uncertain"
            it["safety_note"] = "Suitability during pregnancy cannot be established reliably. Check ground conditions, shade, and stairs locally before proceeding."

        if mobility and (has_stairs_val or strenuous):
            it["accessibility_flag"] = "accessibility_uncertain"
            it["accessibility_note"] = "Accessibility cannot be assumed without reliable local information; site may feature steps or uneven paving."

        if senior and has_stairs_val:
            it["safety_note"] = "Site involves stairs or inclines; recommended to visit at an easy pace with rest intervals."

        if less_walking and (it["estimated_duration_minutes"] > 120 or e >= 45):
            it["safety_note"] = "Higher walking workload; allow extra seating breaks."

        if is_mandatory:
            mandatory_items.append(it)
        else:
            optional_items.append(it)

    # Group items by city
    mandatory_by_city: dict[str, list[dict]] = {}
    for it in mandatory_items:
        mandatory_by_city.setdefault(it["city"], []).append(it)

    optional_by_city: dict[str, list[dict]] = {}
    for it in optional_items:
        optional_by_city.setdefault(it["city"], []).append(it)

    # Determine target cities to visit
    all_active_cities = set(mandatory_by_city.keys()) | set(optional_by_city.keys())
    target_cities = [c for c in order if c in all_active_cities or c in (cities or [])]
    if not target_cities:
        target_cities = list(all_active_cities) or ["Trip"]

    day_buckets: list[dict] = []

    def fits(bucket_stops, extra, extra_city, bucket_cities, limit):
        load = sum(s["effort"] for s in bucket_stops) + extra["effort"]
        cities_after = bucket_cities | ({extra_city} if extra_city else set())
        if len(cities_after) > 1:
            load += CITY_CHANGE_COST
        return load <= limit and len(bucket_stops) < max_stops

    if target_cities and n_days >= len(target_cities):
        # Assign at least 1 day per target city, then distribute extra days
        alloc = {c: 1 for c in target_cities}
        remaining_days = n_days - len(target_cities)

        for _ in range(remaining_days):
            # Prioritize city with more mandatory stops first
            cand = [c for c in target_cities if alloc[c] < len(mandatory_by_city.get(c, []))]
            if not cand:
                # Then check city with highest total effort load
                best = max(
                    target_cities,
                    key=lambda c: (
                        sum(s["effort"] for s in mandatory_by_city.get(c, [])) +
                        sum(s["effort"] for s in optional_by_city.get(c, []))
                    ) / alloc[c]
                )
            else:
                best = max(cand, key=lambda c: len(mandatory_by_city.get(c, [])) / alloc[c])
            alloc[best] += 1

        for c in target_cities:
            c_mandatory = mandatory_by_city.get(c, [])
            c_optional = optional_by_city.get(c, [])
            buckets = [{"assigned_city": c, "stops": []} for _ in range(alloc[c])]

            # ---------------------------------------------------------
            # 1. Schedule Mandatory Attractions First
            # Sort by must-visit flag, then visit_order / input order.
            # DO NOT sort by effort points, so important stops aren't pushed out!
            # ---------------------------------------------------------
            c_mandatory_sorted = sorted(
                c_mandatory,
                key=lambda x: (0 if x["is_must_visit"] else 1, x["visit_order"])
            )

            for s in c_mandatory_sorted:
                options = [
                    b for b in buckets
                    if fits(b["stops"], s, c, {s_item["city"] for s_item in b["stops"]}, cap)
                ] or [
                    b for b in buckets
                    if fits(b["stops"], s, c, {s_item["city"] for s_item in b["stops"]}, cap * STRETCH)
                ]
                if not options:
                    # Mandatory fallback: allow 1 extra stop or up to 1.30 cap stretch if needed
                    options = [
                        b for b in buckets
                        if len(b["stops"]) <= max_stops and (sum(x["effort"] for x in b["stops"]) + s["effort"]) <= cap * 1.30
                    ]

                if options:
                    min(options, key=lambda b: sum(x["effort"] for x in b["stops"]))["stops"].append(s)
                else:
                    deferred.append({
                        **s,
                        "code": "no_room",
                        "reason": (
                            f"Unable to schedule '{s['name']}' without overloading the {alloc[c]} day(s) "
                            f"allocated to {c}. Daily capacity is reached. Consider adding a day to {c}."
                        ),
                    })

            # ---------------------------------------------------------
            # 2. Schedule Optional Attractions Only After Mandatory Are Accommodated
            # ---------------------------------------------------------
            c_optional_sorted = sorted(
                c_optional,
                key=lambda x: (0 if x["is_must_visit"] else 1, -x["effort"])
            )
            for s in c_optional_sorted:
                options = [
                    b for b in buckets
                    if fits(b["stops"], s, c, {s_item["city"] for s_item in b["stops"]}, cap)
                ]
                if options:
                    min(options, key=lambda b: sum(x["effort"] for x in b["stops"]))["stops"].append(s)

            day_buckets.extend(buckets)

        while len(day_buckets) < n_days:
            last_city = target_cities[-1] if target_cities else "Trip"
            day_buckets.append({"assigned_city": last_city, "stops": []})

    elif target_cities:
        # Fewer days than cities: fill days in order
        day_buckets = [
            {"assigned_city": target_cities[min(i, len(target_cities) - 1)], "stops": []}
            for i in range(n_days)
        ]
        d = 0
        for c in target_cities:
            c_items = mandatory_by_city.get(c, []) + optional_by_city.get(c, [])
            c_sorted = sorted(c_items, key=lambda x: (0 if x["is_mandatory"] else 1, 0 if x["is_must_visit"] else 1))
            for s in c_sorted:
                placed = False
                for limit in (cap, cap * STRETCH):
                    for dd in range(d, n_days):
                        b = day_buckets[dd]
                        current_cities = {s_item["city"] for s_item in b["stops"]}
                        if fits(b["stops"], s, c, current_cities, limit):
                            b["stops"].append(s)
                            d, placed = dd, True
                            break
                    if placed:
                        break
                if not placed and s["is_mandatory"]:
                    deferred.append({
                        **s,
                        "code": "no_room",
                        "reason": f"Not enough days in itinerary to fit '{s['name']}' without exceeding safe physical limits.",
                    })
    else:
        day_buckets = [{"assigned_city": "Trip", "stops": []} for _ in range(n_days)]

    # Finalize days with base dates and weather adjustments
    days = []
    base_date = None
    if start_date:
        if isinstance(start_date, date):
            base_date = start_date
        elif isinstance(start_date, str):
            try:
                base_date = date.fromisoformat(start_date[:10])
            except ValueError:
                base_date = None

    # Weather lookup table by (destination_lower, date_iso)
    weather_by_city_date: dict[tuple[str, str], dict] = {}
    if weather_data:
        for entry in weather_data:
            dest = str(entry.get("destination", "")).strip().lower()
            d_str = str(entry.get("date", "")).strip()
            if dest and d_str:
                weather_by_city_date[(dest, d_str)] = entry

    for i, b in enumerate(day_buckets[:n_days], start=1):
        ordered = _order_day(b["stops"])

        # City set matching actual scheduled stops
        actual_cities: list[str] = []
        for s in ordered:
            c = s.get("city")
            if c and c not in actual_cities:
                actual_cities.append(c)

        if not actual_cities:
            assigned = b.get("assigned_city")
            actual_cities = [assigned] if assigned and assigned != "Trip" else []

        day_dest = " + ".join(actual_cities) if actual_cities else "Flexible"
        city_change = len(actual_cities) > 1
        total = sum(s["effort"] for s in ordered) + (CITY_CHANGE_COST if city_change else 0)

        day_date_str = (base_date + timedelta(days=i - 1)).isoformat() if base_date else None

        # Check weather forecast for this day and destination
        weather_alert_present = False
        rain_prob = None
        if day_date_str and actual_cities and weather_by_city_date:
            for c_name in actual_cities:
                key = (c_name.lower(), day_date_str)
                w_match = weather_by_city_date.get(key)
                if not w_match:
                    # Partial match
                    for (w_c, w_d), w_entry in weather_by_city_date.items():
                        if w_d == day_date_str and (w_c in c_name.lower() or c_name.lower() in w_c):
                            w_match = w_entry
                            break
                if w_match:
                    prob = w_match.get("precipitation_probability_max")
                    if prob is not None and prob >= 40:
                        weather_alert_present = True
                        rain_prob = prob
                        break

        notes = []
        if not ordered:
            status = "free"
            notes.append("Free day: rest or keep it flexible.")
        elif total > cap * 0.85:
            status = "heavy"
            notes.append("Active day: recommended to take relaxed lunch and evening pauses.")
        elif total < cap * 0.35:
            status = "light"
            notes.append("Light day: easy pace with plenty of leisure time.")
        else:
            status = "ok"

        if city_change:
            notes.append("Multiple cities in one day: travel time is counted as effort.")

        # Traveller preference specific day notes
        if senior:
            notes.append("Paced for senior citizens: scheduled rest intervals between activities and manageable walking workloads.")
        if pregnant:
            notes.append("Paced for pregnancy comfort: strenuous activities avoided; check local shade and seating availability.")
        if mobility:
            notes.append("Mobility considerations applied: verify on-site ramps or assistance for historical structures.")
        if less_walking:
            notes.append("Paced for less walking: shorter walks and comfortable transit intervals.")
        if easy_pace:
            notes.append("Easy pace: unhurried exploration with extra downtime.")

        # Weather notes on stops and day
        if weather_alert_present and rain_prob is not None:
            notes.append(f"Weather alert: High chance of precipitation ({rain_prob}%). Plan indoor visits during rain windows.")
            for s in ordered:
                if not _is_indoor(s):
                    s["weather_note"] = f"Precipitation probability {rain_prob}%. Plan during clearer hours or carry rain gear."
                elif rain_friendly:
                    s["weather_note"] = "Sheltered indoor venue ideal for rainy conditions."

        days.append({
            "day": i,
            "day_number": i,
            "date": day_date_str,
            "cities": actual_cities,
            "destination": day_dest,
            "stops": ordered,
            "total": total,
            "capacity": cap,
            "status": status,
            "notes": notes,
        })

    warnings = []
    active_cities_count = len([c for c in target_cities if (mandatory_by_city.get(c) or optional_by_city.get(c))])
    if active_cities_count > n_days:
        warnings.append(
            f"You picked {active_cities_count} cities with places to visit, but only have {n_days} day(s). "
            f"Add days to cover every city comfortably."
        )
    if any(x["code"] == "no_room" for x in deferred):
        warnings.append("Some selected places could not fit without overloading the schedule. Add days or adjust selections.")
    if any(x["code"] in {"strenuous", "avoid_strenuous"} for x in deferred):
        warnings.append("Strenuous activities were set aside to match the group's physical preference.")
    if any(x["code"] == "unsuitable_pregnancy" for x in deferred):
        warnings.append("Activities involving strenuous climbs or rough terrain were set aside for pregnancy safety.")
    if any(d["status"] == "heavy" for d in days):
        warnings.append("One or more days have high physical effort. We recommend taking longer meal breaks.")

    return {
        "days": days,
        "deferred": deferred,
        "unscheduled": deferred,
        "warnings": warnings,
        "summary": {
            "capacity": cap,
            "max_stops": max_stops,
            "single_limit": single_limit,
            "paced_for": _paced_for(profile),
            "pace": pace,
            "total_effort": sum(d["total"] for d in days),
            "total_days": n_days,
            "scheduled_count": sum(len(d["stops"]) for d in days),
            "deferred_count": len(deferred),
        },
    }


def to_prompt(p: dict) -> str:
    """Text block to append to your Gemini itinerary prompt. Gemini narrates; it does not re-plan."""
    lines = [
        "AUTHORITATIVE NAMMA GATI DAILY ATTRACTION SCHEDULE:",
        "This schedule was calculated by our stamina-aware pacing engine. You MUST follow it strictly.",
        "- Do NOT add, remove, or move attractions between days.",
        "- Keep each scheduled attraction on its assigned day and destination.",
        "- Preserve attraction IDs and names exactly.",
    ]
    for d in p.get("days", []):
        where = " + ".join(d.get("cities", [])) or d.get("destination") or "flexible"
        if d.get("stops"):
            stops = "; ".join(f'[{s["id"]}] {s["name"]} ({s.get("category", "Attraction")})' for s in d["stops"])
            lines.append(f'Day {d["day"]} ({where}): {stops}')
        else:
            lines.append(f'Day {d["day"]} ({where}): Free / flexible day. Suggest light leisure or rest.')

    paced_for = p.get("summary", {}).get("paced_for", [])
    if paced_for:
        lines.append(f"Group pace profile: paced for {', '.join(paced_for)}. Keep rest breaks and physical intensity suitable.")

    lines.append(
        "For each day, integrate breakfast first, lunch midday, and dinner in the evening, "
        "choosing ONLY from the provided food spots of that day's city."
    )

    if p.get("deferred"):
        why = {
            "strenuous": "too strenuous for group stamina profile",
            "no_room": "no room in the daily schedule",
            "avoid_strenuous": "excluded because 'Avoid strenuous treks' was requested",
            "unsuitable_pregnancy": "excluded for pregnancy safety",
        }
        lines.append(
            "These attractions were set aside by Namma Gati and must NOT be added to any day's stops: " +
            "; ".join(f'{x["name"]} ({why.get(x.get("code"), "deferred")})' for x in p["deferred"])
        )

    return "\n".join(lines)
