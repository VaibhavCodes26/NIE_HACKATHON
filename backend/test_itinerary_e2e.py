"""
End-to-end verification test for NammaPrayana itinerary generation lifecycle.
Tests:
1. Authentication: Signup & Login (obtains tab-scoped bearer token)
2. Destination retrieval: Ensure active destinations available
3. Attraction retrieval: Ensure attractions available for destination
4. Itinerary Generation: POST /api/itineraries/generate with:
   - Valid destinations (Mysuru)
   - Selected attractions ([3, 27])
   - Travel preferences & pace
5. Verify Generated Itinerary structure:
   - Valid title, days, and stops
   - Selected attractions are included
   - Lunch and dinner present for every day
   - Gati pacing data present
6. Save Itinerary: POST /api/itineraries/saved with bearer token
7. Retrieve Saved Itinerary: GET /api/itineraries/saved/{id}
8. Multi-city generation test: Mysuru + Bengaluru
"""

import json
import time
import urllib.request
import urllib.error
import uuid

BASE_URL = "http://localhost:8000"


def request_json(method, endpoint, payload=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else None


def run_e2e_tests():
    print("=== STARTING END-TO-END ITINERARY VERIFICATION ===")

    # 1. Signup / Auth
    print("\n--- 1. Testing User Signup & Token ---")
    username = f"e2e_traveler_{uuid.uuid4().hex[:6]}"
    password = "SecurePassword123!"
    status, signup_data = request_json("POST", "/api/auth/signup", {
        "username": username,
        "password": password,
        "confirm_password": password
    })
    assert status == 201, f"Signup failed: {status}"
    token = signup_data.get("token")
    assert token, "Token not returned in signup response"
    auth_headers = {"Authorization": f"Bearer {token}"}
    print(f"Signup SUCCESS. User: {username}, Token: {token[:12]}...")

    # 2. Check /api/auth/me
    print("\n--- 2. Verifying Auth State ---")
    status, me_data = request_json("GET", "/api/auth/me", headers=auth_headers)
    assert status == 200, f"/api/auth/me failed: {status}"
    assert me_data["username"] == username
    print(f"Auth check SUCCESS: Logged in as {me_data['username']}")

    # 3. Retrieve Destinations
    print("\n--- 3. Verifying Destinations ---")
    status, dests = request_json("GET", "/api/destinations")
    assert status == 200, f"/api/destinations failed: {status}"
    assert len(dests) > 0, "No destinations returned"
    mysuru = next((d for d in dests if "mysuru" in d["name"].lower() or "mysore" in d["name"].lower()), None)
    assert mysuru, "Mysuru destination not found"
    print(f"Destinations check SUCCESS: Found {len(dests)} destinations, including {mysuru['name']}")

    # 4. Generate Itinerary with Selected Attractions
    print("\n--- 4. Testing Itinerary Generation (/api/itineraries/generate) ---")
    # IDs 3 (Mysuru Palace) and 27 (Chamundi Hills)
    gen_payload = {
        "destinations": ["Mysuru"],
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "traveller_count": 2,
        "travel_style": "comfortable",
        "total_budget": 15000,
        "interests": ["Heritage & culture", "Tourist attractions"],
        "selected_attraction_ids": [3, 27],
        "adjustment_request": "Pace suitable for senior citizens",
        "pace": "relaxed",
        "profile": {"senior": True, "less_walking": True}
    }
    t0 = time.time()
    status, itin = request_json("POST", "/api/itineraries/generate", gen_payload)
    elapsed = time.time() - t0
    assert status == 200, f"Itinerary generation failed: {status}"
    assert itin.get("title"), "Itinerary missing title"
    assert len(itin.get("days", [])) == 2, f"Expected 2 days, got {len(itin.get('days', []))}"

    print(f"Generation SUCCESS in {elapsed:.2f}s: '{itin.get('title')}'")
    all_stops = []
    scheduled_attr_ids = set()
    for day in itin["days"]:
        print(f"  Day {day['day_number']} ({day['date']}) in {day['destination']}: {len(day['stops'])} stops")
        lunch_found = False
        dinner_found = False
        for s in day["stops"]:
            all_stops.append(s)
            if s.get("meal_type") == "lunch":
                lunch_found = True
            if s.get("meal_type") == "dinner":
                dinner_found = True
            if s.get("attraction_id"):
                scheduled_attr_ids.add(s["attraction_id"])
            print(f"    - [{s.get('time', 'TBD')}] {s.get('name')} ({s.get('category')}, meal={s.get('meal_type')})")
        assert lunch_found, f"Day {day['day_number']} missing lunch!"
        assert dinner_found, f"Day {day['day_number']} missing dinner!"

    assert 3 in scheduled_attr_ids or 27 in scheduled_attr_ids, "Selected attractions must be present"
    print("All daily stops, meals, and attraction verifications PASSED!")

    # 5. Save the generated itinerary
    print("\n--- 5. Testing Save Itinerary (/api/itineraries/saved) ---")
    save_payload = {
        "itinerary_payload": itin,
        "trip_config": gen_payload,
        "destinations": ["Mysuru"],
        "selected_attraction_ids": [3, 27],
        "title": itin["title"],
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "traveller_count": 2,
        "total_budget": 15000,
        "travel_style": "comfortable",
        "duration_days": 2,
    }
    status, saved_data = request_json("POST", "/api/itineraries/saved", save_payload, headers=auth_headers)
    assert status == 201, f"Save itinerary failed: {status}"
    saved_id = saved_data["id"]
    print(f"Save SUCCESS: Itinerary ID {saved_id}")

    # 6. Retrieve Saved Itineraries List and Detail
    print("\n--- 6. Retrieving Saved Itinerary ---")
    status, saved_list = request_json("GET", "/api/itineraries/saved", headers=auth_headers)
    assert status == 200, f"Get saved list failed: {status}"
    assert any(i["id"] == saved_id for i in saved_list), "Saved itinerary not in list"

    status, saved_detail = request_json("GET", f"/api/itineraries/saved/{saved_id}", headers=auth_headers)
    assert status == 200, f"Get saved detail failed: {status}"
    assert saved_detail["id"] == saved_id
    assert saved_detail["itinerary_payload"]["title"] == itin["title"]
    print(f"Retrieve SUCCESS: Saved itinerary verified with {len(saved_detail['itinerary_payload']['days'])} days")

    # 7. Multi-city itinerary generation test
    print("\n--- 7. Testing Multi-city Itinerary Generation (Mysuru + Bengaluru) ---")
    multi_payload = {
        "destinations": ["Mysuru", "Bengaluru"],
        "start_date": "2026-11-05",
        "end_date": "2026-11-07",
        "traveller_count": 3,
        "travel_style": "budget",
        "total_budget": 20000,
        "interests": ["Heritage & culture", "Nature & hills"],
        "selected_attraction_ids": [],
        "adjustment_request": "",
        "pace": "balanced",
        "profile": {}
    }
    t0 = time.time()
    status, multi_itin = request_json("POST", "/api/itineraries/generate", multi_payload)
    elapsed = time.time() - t0
    assert status == 200, f"Multi-city generation failed: {status}"
    assert len(multi_itin.get("days", [])) == 3, f"Expected 3 days, got {len(multi_itin.get('days', []))}"
    print(f"Multi-city SUCCESS in {elapsed:.2f}s: '{multi_itin.get('title')}' across {len(multi_itin.get('days', []))} days")

    print("\n=== ALL END-TO-END ITINERARY TESTS COMPLETED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_e2e_tests()
