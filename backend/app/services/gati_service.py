"""
Namma Gati: stamina-aware pacing for itineraries.

Pure Python. No API calls, no tokens. Runs BEFORE Gemini:
    selected attractions -> effort score each -> fit into days under a per-day
    stamina budget (lower for seniors / pregnancy / children / mobility needs)
    -> Gemini only narrates the fixed plan (adds meals, timings, descriptions).

The effort numbers are editorial ratings (our own estimates), not measurements.
Tune RULES / EFFORT_OVERRIDES freely, or store an `effort` (0-100) column in your DB.
"""
import re
from datetime import date, timedelta
from typing import Any, Optional

BASE_CAPACITY = 110      # effort points a healthy adult group can handle per day
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


def plan(
    stops: list,
    n_days: int,
    profile: Optional[dict] = None,
    cities: Optional[list] = None,
    pace: str = "balanced",
    start_date: Optional[Any] = None,
) -> dict:
    """
    Deterministic stamina-aware itinerary allocator.
    Allocates attractions across n_days respecting city order, capacity, and group limits.
    """
    n_days = max(1, int(n_days or 1))
    cap = capacity(profile, pace)
    max_stops = max(2, round(cap / 22))
    single_limit = round(cap * 0.8)

    # Clean and order requested cities
    order: list[str] = []
    for c in (cities or []):
        c_str = str(c).strip()
        if c_str and c_str not in order:
            order.append(c_str)

    # Process and deduplicate stops
    seen_ids = set()
    items, deferred = [], []

    for a in stops:
        stop_id = a.get("id")
        if stop_id is not None:
            if stop_id in seen_ids:
                continue
            seen_ids.add(stop_id)

        e = effort_of(a)
        city = _resolve_city(a, order)

        # Ensure city is in order list if new
        if city and city not in order and city != "Trip":
            order.append(city)

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
        }

        if e > single_limit:
            deferred.append({
                **it,
                "code": "strenuous",
                "reason": f"Too strenuous for this group (effort {e}, comfortable limit {single_limit}).",
            })
        else:
            items.append(it)

    by_city: dict[str, list[dict]] = {}
    for it in items:
        by_city.setdefault(it["city"], []).append(it)

    # Target cities to visit
    target_cities = [c for c in order if c in by_city or c in (cities or [])]
    if not target_cities:
        target_cities = list(by_city.keys())

    day_buckets: list[dict] = []

    def fits(bucket_stops, extra, extra_city, bucket_cities, limit):
        load = sum(s["effort"] for s in bucket_stops) + extra["effort"]
        cities_after = bucket_cities | ({extra_city} if extra_city else set())
        if len(cities_after) > 1:
            load += CITY_CHANGE_COST
        return load <= limit and len(bucket_stops) < max_stops

    def deferral(s, code, reason):
        deferred.append({**s, "code": code, "reason": reason})

    if target_cities and n_days >= len(target_cities):
        # Assign at least 1 day per target city, then distribute extra days
        alloc = {c: 1 for c in target_cities}
        remaining_days = n_days - len(target_cities)

        for _ in range(remaining_days):
            cand = [c for c in target_cities if alloc[c] < len(by_city.get(c, []))]
            if not cand:
                # If all cities have as many days as attractions, give to city with highest total load
                best = max(target_cities, key=lambda c: sum(s["effort"] for s in by_city.get(c, [])) / alloc[c])
            else:
                best = max(cand, key=lambda c: sum(s["effort"] for s in by_city.get(c, [])) / alloc[c])
            alloc[best] += 1

        for c in target_cities:
            city_stops = by_city.get(c, [])
            buckets = [{"assigned_city": c, "stops": []} for _ in range(alloc[c])]
            for s in sorted(city_stops, key=lambda x: -x["effort"]):
                options = [
                    b for b in buckets
                    if fits(b["stops"], s, c, {s_item["city"] for s_item in b["stops"]}, cap)
                ] or [
                    b for b in buckets
                    if fits(b["stops"], s, c, {s_item["city"] for s_item in b["stops"]}, cap * STRETCH)
                ]
                if options:
                    min(options, key=lambda b: sum(x["effort"] for x in b["stops"]))["stops"].append(s)
                else:
                    deferral(s, "no_room", "No room without overloading a day. Add a day or remove another stop.")
            day_buckets.extend(buckets)

        while len(day_buckets) < n_days:
            last_city = target_cities[-1] if target_cities else "Trip"
            day_buckets.append({"assigned_city": last_city, "stops": []})

    elif target_cities:
        # Fewer days than cities: fill days in order, charging for city changes
        day_buckets = [{"assigned_city": target_cities[min(i, len(target_cities) - 1)], "stops": []} for i in range(n_days)]
        d = 0
        for c in target_cities:
            for s in sorted(by_city.get(c, []), key=lambda x: -x["effort"]):
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
                if not placed:
                    deferral(s, "no_room", "Not enough days for this stop without exhausting the group.")
    else:
        day_buckets = [{"assigned_city": "Trip", "stops": []} for _ in range(n_days)]

    # Finalize days: build accurate scheduled stops and city sets
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

        notes = []
        if not ordered:
            status = "free"
            notes.append("Free day: rest or keep it flexible.")
        elif total > cap * 0.85:
            status = "heavy"
            notes.append("Heavy day: do the hardest stop first and keep a long lunch break.")
        elif total < cap * 0.35:
            status = "light"
            notes.append("Light day: easy pace with plenty of leisure time.")
        else:
            status = "ok"

        if city_change:
            notes.append("Multiple cities in one day: travel time is counted as effort.")

        day_date_str = (base_date + timedelta(days=i - 1)).isoformat() if base_date else None

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
    active_cities_count = len([c for c in target_cities if by_city.get(c)])
    if active_cities_count > n_days:
        warnings.append(
            f"You picked {active_cities_count} cities with places to visit, but only have {n_days} day(s). "
            f"Add days to cover every city comfortably."
        )
    if any(x["code"] == "no_room" for x in deferred):
        warnings.append("Some places did not fit without overloading a day. Add a day or remove another stop.")
    if any(x["code"] == "strenuous" for x in deferred):
        warnings.append("Some places are too strenuous for this group's stamina profile and were set aside.")
    if any(d["status"] == "heavy" for d in days):
        warnings.append("One or more days have high physical effort. We recommend taking longer meal breaks.")

    return {
        "days": days,
        "deferred": deferred,
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
        why = {"strenuous": "too strenuous for this group profile", "no_room": "no room in the schedule"}
        lines.append(
            "These attractions were set aside by Namma Gati and must NOT be added to any day's stops: " +
            "; ".join(f'{x["name"]} ({why.get(x.get("code"), "deferred")})' for x in p["deferred"])
        )

    return "\n".join(lines)
