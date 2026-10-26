"""Test suite for NammaPrayana Authentication and Saved Itineraries."""

import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_and_itineraries_lifecycle():
    # 1. Unauthenticated checks
    res = client.get("/api/auth/me")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    res = client.get("/api/itineraries/saved")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    # 2. Signup User A
    user_a_name = f"traveler_{uuid.uuid4().hex[:6]}"
    password_a = "StrongPass123!"

    # Mismatched passwords
    res = client.post("/api/auth/signup", json={
        "username": user_a_name,
        "password": password_a,
        "confirm_password": "WrongPassword123!"
    })
    assert res.status_code == 422, f"Expected 422, got {res.status_code}"

    # Valid signup
    res = client.post("/api/auth/signup", json={
        "username": user_a_name,
        "password": password_a,
        "confirm_password": password_a
    })
    assert res.status_code == 201, f"Expected 201, got {res.status_code}"
    user_a_data = res.json()
    assert user_a_data["username"] == user_a_name
    token_a = user_a_data["token"]
    assert token_a, "Expected token in signup response"
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Duplicate username signup rejected
    res = client.post("/api/auth/signup", json={
        "username": user_a_name,
        "password": password_a,
        "confirm_password": password_a
    })
    assert res.status_code == 409, f"Expected 409, got {res.status_code}"

    # 3. Check current user for User A using tab-scoped Bearer token
    res = client.get("/api/auth/me", headers=headers_a)
    assert res.status_code == 200
    assert res.json()["username"] == user_a_name

    # 4. Save Itinerary for User A
    itin_payload = {
        "title": "Mysuru Royal Heritage",
        "days": [
            {
                "day_number": 1,
                "date": "2026-11-01",
                "theme": "Palaces and Art",
                "stops": [
                    {"name": "Mysore Palace", "time": "09:30 AM", "type": "heritage"}
                ]
            }
        ]
    }
    trip_config = {
        "destinations": ["Mysuru"],
        "startDate": "2026-11-01",
        "endDate": "2026-11-01",
        "travellerCount": 2,
        "travelStyle": "heritage",
        "totalBudget": 5000,
        "interests": ["history", "palaces"]
    }

    res = client.post("/api/itineraries/saved", json={
        "itinerary_payload": itin_payload,
        "trip_config": trip_config,
        "destinations": ["Mysuru"],
        "selected_attraction_ids": [101, 102],
        "title": "Mysuru Royal Heritage",
        "start_date": "2026-11-01",
        "end_date": "2026-11-01",
        "traveller_count": 2,
        "total_budget": 5000,
        "travel_style": "heritage",
        "duration_days": 1
    }, headers=headers_a)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}"
    itin_a = res.json()
    itin_a_id = itin_a["id"]
    assert itin_a["title"] == "Mysuru Royal Heritage"
    assert itin_a["duration_days"] == 1

    # 5. List Itineraries for User A
    res = client.get("/api/itineraries/saved", headers=headers_a)
    assert res.status_code == 200
    itineraries_list = res.json()
    assert len(itineraries_list) >= 1
    assert any(item["id"] == itin_a_id for item in itineraries_list)

    # 6. Get Specific Itinerary for User A
    res = client.get(f"/api/itineraries/saved/{itin_a_id}", headers=headers_a)
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == itin_a_id
    assert "itinerary_payload" in detail
    assert detail["itinerary_payload"]["title"] == "Mysuru Royal Heritage"

    # 7. Signup User B and test Data Isolation
    user_b_name = f"traveler_{uuid.uuid4().hex[:6]}"
    password_b = "StrongPass456!"
    res = client.post("/api/auth/signup", json={
        "username": user_b_name,
        "password": password_b,
        "confirm_password": password_b
    })
    assert res.status_code == 201
    token_b = res.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B list should NOT contain User A's itinerary
    res = client.get("/api/itineraries/saved", headers=headers_b)
    assert res.status_code == 200
    user_b_list = res.json()
    assert not any(item["id"] == itin_a_id for item in user_b_list)

    # User B cannot access User A's itinerary (returns 404)
    res = client.get(f"/api/itineraries/saved/{itin_a_id}", headers=headers_b)
    assert res.status_code == 404

    # User B cannot delete User A's itinerary (returns 404)
    res = client.delete(f"/api/itineraries/saved/{itin_a_id}", headers=headers_b)
    assert res.status_code == 404

    # 8. User A can delete their own itinerary
    res = client.delete(f"/api/itineraries/saved/{itin_a_id}", headers=headers_a)
    assert res.status_code == 204

    # Verify deleted
    res = client.get(f"/api/itineraries/saved/{itin_a_id}", headers=headers_a)
    assert res.status_code == 404

    # 9. Logout
    res = client.post("/api/auth/logout", headers=headers_a)
    assert res.status_code == 200

    # User A session is now invalid
    res = client.get("/api/auth/me", headers=headers_a)
    assert res.status_code == 401

    print("ALL AUTH AND ITINERARY TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_auth_and_itineraries_lifecycle()
