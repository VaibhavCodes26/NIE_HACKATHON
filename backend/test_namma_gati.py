"""
Comprehensive test suite for Namma Gati stamina-aware itinerary planning.
Uses unittest and FastAPI TestClient with mocked Gemini calls.
"""
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import gati_service
from app.services.gemini_service import _validate_and_enforce_daily_structure


class TestNammaGatiEngine(unittest.TestCase):
    """Unit tests for Gati effort scoring, capacity, and scheduling."""

    def test_effort_overrides(self):
        # Known strenuous overrides
        self.assertEqual(gati_service.effort_of({"name": "Kudremukh Peak Trek"}), 85)
        self.assertEqual(gati_service.effort_of({"name": "Mullayanagiri Peak"}), 70)
        self.assertEqual(gati_service.effort_of({"name": "Shravanabelagola Monolith"}), 75)
        self.assertEqual(gati_service.effort_of({"name": "Savandurga Fort Trek"}), 80)

    def test_effort_rules_and_categories(self):
        # Regex rules
        self.assertEqual(gati_service.effort_of({"name": "Jog Falls", "category": "Waterfalls"}), 50)
        self.assertEqual(gati_service.effort_of({"name": "Mysore Palace", "category": "Palace"}), 30)
        self.assertEqual(gati_service.effort_of({"name": "Sunset Viewpoint", "category": "Viewpoint"}), 15)

    def test_duration_handling(self):
        # Duration in hours (> 2 adds points)
        base = gati_service.effort_of({"name": "Mysore Palace", "category": "Palace"})
        with_hours = gati_service.effort_of({
            "name": "Mysore Palace",
            "category": "Palace",
            "duration_hours": 4.0,
        })
        self.assertEqual(with_hours, base + 10)

        # Duration in estimated_duration_minutes from database (180 mins = 3 hours -> adds 5)
        with_mins = gati_service.effort_of({
            "name": "Mysore Palace",
            "category": "Palace",
            "estimated_duration_minutes": 180,
        })
        self.assertEqual(with_mins, base + 5)

    def test_explicit_effort_clamping(self):
        self.assertEqual(gati_service.effort_of({"name": "Custom", "effort": 150}), 100)
        self.assertEqual(gati_service.effort_of({"name": "Custom", "effort": -10}), 0)
        self.assertEqual(gati_service.effort_of({"name": "Custom", "effort": 45}), 45)

    def test_capacity_and_profile_pacing(self):
        # Healthy adult baseline
        self.assertEqual(gati_service.capacity(None, "balanced"), 110)
        self.assertEqual(gati_service.capacity(None, "relaxed"), 88)
        self.assertEqual(gati_service.capacity(None, "packed"), 132)

        # Senior citizen (70% multiplier)
        self.assertEqual(gati_service.capacity({"senior": True}, "balanced"), 77)

        # Mobility limitations (55% multiplier)
        self.assertEqual(gati_service.capacity({"mobility": True}, "balanced"), 61)

        # Multiple flags: weakest traveller sets pace (mobility 0.55 < senior 0.70)
        self.assertEqual(gati_service.capacity({"senior": True, "mobility": True}, "balanced"), 61)

    def test_exact_trip_days_and_ordering(self):
        stops = [
            {"id": 1, "name": "Mysore Palace", "city": "Mysuru"},
            {"id": 2, "name": "Chamundi Hill", "city": "Mysuru"},
            {"id": 3, "name": "Virupaksha Temple", "city": "Hampi"},
        ]
        cities = ["Mysuru", "Hampi"]

        # 3-day plan for 2 cities -> exactly 3 days
        res = gati_service.plan(stops=stops, n_days=3, cities=cities, start_date="2026-11-01")
        self.assertEqual(len(res["days"]), 3)
        self.assertEqual(res["days"][0]["day"], 1)
        self.assertEqual(res["days"][1]["day"], 2)
        self.assertEqual(res["days"][2]["day"], 3)
        self.assertEqual(res["days"][0]["date"], "2026-11-01")
        self.assertEqual(res["days"][1]["date"], "2026-11-02")
        self.assertEqual(res["days"][2]["date"], "2026-11-03")

        # Destination order preserved: Mysuru first, then Hampi
        self.assertIn("Mysuru", res["days"][0]["cities"])

    def test_attraction_to_city_mapping_prevents_trip_fallback(self):
        # Attraction with destination_id instead of direct city
        stops = [
            {"id": 10, "name": "Mysore Zoo", "destination_id": "mysuru", "category": "Zoo"},
            {"id": 20, "name": "Stone Chariot", "destination_id": "hampi", "category": "Monument"},
        ]
        res = gati_service.plan(stops=stops, n_days=2, cities=["Mysuru", "Hampi"])

        day1_cities = res["days"][0]["cities"]
        day2_cities = res["days"][1]["cities"]
        self.assertNotIn("Trip", day1_cities)
        self.assertNotIn("Trip", day2_cities)
        self.assertIn("Mysuru", day1_cities)
        self.assertIn("Hampi", day2_cities)

    def test_duplicate_attraction_ids(self):
        stops = [
            {"id": 1, "name": "Mysore Palace", "city": "Mysuru"},
            {"id": 1, "name": "Mysore Palace Duplicate", "city": "Mysuru"},
            {"id": 2, "name": "Brindavan Gardens", "city": "Mysuru"},
        ]
        res = gati_service.plan(stops=stops, n_days=2, cities=["Mysuru"])
        all_scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertEqual(all_scheduled_ids.count(1), 1)

    def test_strenuous_deferral(self):
        # For a senior group, capacity = 77, single_limit = 62
        # Kudremukh (85) exceeds 62 -> must be deferred as strenuous
        stops = [
            {"id": 101, "name": "Kudremukh Peak Trek", "city": "Chikkamagaluru"},
            {"id": 102, "name": "Coffee Museum", "city": "Chikkamagaluru"},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=2,
            profile={"senior": True},
            cities=["Chikkamagaluru"],
        )
        deferred_codes = [x["code"] for x in res["deferred"]]
        deferred_ids = [x["id"] for x in res["deferred"]]
        self.assertIn("strenuous", deferred_codes)
        self.assertIn(101, deferred_ids)

        # Non-strenuous attraction is scheduled
        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertIn(102, scheduled_ids)
        self.assertNotIn(101, scheduled_ids)

    def test_no_room_deferral(self):
        # Pack 15 strenuous items into 1 day -> excess items must be deferred as "no_room"
        stops = [
            {"id": i, "name": f"Fort {i}", "category": "Fort", "city": "Chitradurga", "effort": 45}
            for i in range(1, 16)
        ]
        res = gati_service.plan(stops=stops, n_days=1, cities=["Chitradurga"])
        self.assertTrue(any(x["code"] == "no_room" for x in res["deferred"]))
        # No day exceeds stretched capacity
        for d in res["days"]:
            self.assertLessEqual(d["total"], res["summary"]["capacity"] * 1.25)

    def test_free_days_preserved(self):
        # 1 attraction for 3 days -> 2 days stay free
        stops = [{"id": 1, "name": "Mysore Palace", "city": "Mysuru"}]
        res = gati_service.plan(stops=stops, n_days=3, cities=["Mysuru"])
        free_days = [d for d in res["days"] if d["status"] == "free"]
        self.assertEqual(len(free_days), 2)
        self.assertEqual(len(res["days"]), 3)

    def test_city_change_cost_included_for_multi_city_day(self):
        stops = [
            {"id": 1, "name": "Stop A", "city": "City1", "effort": 20},
            {"id": 2, "name": "Stop B", "city": "City2", "effort": 20},
        ]
        # Force both into 1 day
        res = gati_service.plan(stops=stops, n_days=1, cities=["City1", "City2"])
        day = res["days"][0]
        # Total effort = 20 + 20 + CITY_CHANGE_COST (40) = 80
        self.assertEqual(day["total"], 80)
        self.assertTrue(any("travel time is counted as effort" in n for n in day["notes"]))


class TestGeminiIntegrationAndValidation(unittest.TestCase):
    """Test Gati schedule adherence and post-processing validation."""

    def test_to_prompt_generation(self):
        plan_dict = {
            "days": [
                {
                    "day": 1,
                    "cities": ["Mysuru"],
                    "stops": [{"id": 1, "name": "Mysore Palace", "category": "Palace"}],
                },
                {"day": 2, "cities": ["Mysuru"], "stops": []},
            ],
            "deferred": [
                {"id": 99, "name": "Kudremukh Trek", "code": "strenuous"}
            ],
            "summary": {"paced_for": ["senior citizens"], "capacity": 77},
        }
        prompt_text = gati_service.to_prompt(plan_dict)
        self.assertIn("AUTHORITATIVE NAMMA GATI DAILY ATTRACTION SCHEDULE", prompt_text)
        self.assertIn("Day 1 (Mysuru): [1] Mysore Palace (Palace)", prompt_text)
        self.assertIn("Day 2 (Mysuru): Free / flexible day", prompt_text)
        self.assertIn("paced for senior citizens", prompt_text)
        self.assertIn("Kudremukh Trek", prompt_text)

    def test_validation_recovers_dropped_attraction_on_assigned_day(self):
        gati_plan = {
            "days": [
                {
                    "day": 1,
                    "destination": "Mysuru",
                    "stops": [
                        {"id": 1, "name": "Mysore Palace", "effort": 30, "level": "medium"},
                        {"id": 2, "name": "Chamundi Hill", "effort": 55, "level": "high"},
                    ],
                    "total": 85,
                    "capacity": 110,
                    "status": "heavy",
                    "notes": [],
                }
            ],
            "deferred": [],
            "warnings": [],
            "summary": {"capacity": 110},
        }

        # Simulated Gemini output that omitted Chamundi Hill (id 2)
        mock_gemini_result = {
            "title": "Mysuru Tour",
            "days": [
                {
                    "day_number": 1,
                    "destination": "Mysuru",
                    "stops": [
                        {
                            "name": "Mysore Palace",
                            "attraction_id": 1,
                            "time": "10:00 AM - 12:30 PM",
                            "category": "Palace",
                        },
                        {
                            "name": "Mylari Dosa",
                            "category": "Lunch",
                            "meal_type": "lunch",
                            "time": "1:00 PM - 2:00 PM",
                            "food_spot_id": 5,
                        },
                    ],
                }
            ],
            "warnings": [],
        }

        validated = _validate_and_enforce_daily_structure(
            result=mock_gemini_result,
            destinations=["Mysuru"],
            attractions=[
                {"id": 1, "name": "Mysore Palace"},
                {"id": 2, "name": "Chamundi Hill"},
            ],
            food_spots=[
                {"id": 5, "city": "mysuru", "name": "Mylari Dosa"},
                {"id": 6, "city": "mysuru", "name": "Gufha Restaurant"},
            ],
            gati_plan=gati_plan,
        )

        day1_stops = validated["days"][0]["stops"]
        scheduled_ids = [s.get("attraction_id") for s in day1_stops if s.get("attraction_id") is not None]
        self.assertIn(1, scheduled_ids)
        self.assertIn(2, scheduled_ids)  # Chamundi Hill successfully recovered on Day 1

        # Meals enforced
        meals = [s.get("meal_type") for s in day1_stops if s.get("meal_type")]
        self.assertIn("lunch", meals)
        self.assertIn("dinner", meals)

    def test_validation_strips_deferred_attractions_if_model_hallucinates_them(self):
        gati_plan = {
            "days": [
                {
                    "day": 1,
                    "destination": "Chikkamagaluru",
                    "stops": [{"id": 10, "name": "Coffee Museum", "effort": 20, "level": "low"}],
                    "total": 20,
                    "capacity": 77,
                    "status": "light",
                    "notes": [],
                }
            ],
            "deferred": [
                {"id": 99, "name": "Kudremukh Peak Trek", "code": "strenuous", "reason": "Too strenuous"}
            ],
            "warnings": [],
            "summary": {"capacity": 77},
        }

        # Simulated Gemini output that illegally re-inserted Kudremukh (id 99)
        mock_gemini_result = {
            "title": "Chikkamagaluru Trip",
            "days": [
                {
                    "day_number": 1,
                    "destination": "Chikkamagaluru",
                    "stops": [
                        {"name": "Coffee Museum", "attraction_id": 10, "time": "9:30 AM"},
                        {"name": "Kudremukh Peak Trek", "attraction_id": 99, "time": "11:30 AM"},
                    ],
                }
            ],
            "warnings": [],
        }

        validated = _validate_and_enforce_daily_structure(
            result=mock_gemini_result,
            destinations=["Chikkamagaluru"],
            attractions=[{"id": 10, "name": "Coffee Museum"}, {"id": 99, "name": "Kudremukh Peak Trek"}],
            food_spots=[],
            gati_plan=gati_plan,
        )

        day1_attr_ids = [s.get("attraction_id") for s in validated["days"][0]["stops"]]
        self.assertIn(10, day1_attr_ids)
        self.assertNotIn(99, day1_attr_ids)  # Kudremukh Peak Trek stripped out


class TestFastAPIEndpoints(unittest.TestCase):
    """Integration tests for FastAPI /api/gati/plan, /api/itineraries/preview, and generate."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_gati_plan_endpoint(self):
        payload = {
            "stops": [
                {"id": 1, "name": "Mysore Palace", "city": "Mysuru", "category": "Palace"},
                {"id": 2, "name": "Kudremukh Peak Trek", "city": "Chikkamagaluru", "category": "Trek"},
            ],
            "days": 2,
            "cities": ["Mysuru", "Chikkamagaluru"],
            "profile": {"senior": True},
            "pace": "relaxed",
        }
        res = self.client.post("/api/gati/plan", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("days", data)
        self.assertIn("deferred", data)
        self.assertIn("summary", data)
        self.assertEqual(len(data["days"]), 2)
        # Kudremukh deferred for senior group in relaxed pace
        self.assertTrue(any(x["id"] == 2 for x in data["deferred"]))

    def test_itinerary_preview_endpoint(self):
        payload = {
            "destinations": ["mysuru"],
            "start_date": date.today().isoformat(),
            "end_date": date.today().isoformat(),
            "traveller_count": 2,
            "travel_style": "comfortable",
            "total_budget": 10000,
            "interests": ["Heritage & culture"],
            "pace": "balanced",
        }
        res = self.client.post("/api/itineraries/preview", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "preview")
        self.assertIn("gati", data)
        self.assertIn("days", data)
        self.assertEqual(len(data["days"]), 1)
        self.assertIsNotNone(data["days"][0]["effort_total"])

    @patch("app.services.gemini_service.genai.Client")
    def test_itinerary_generate_with_mock_gemini(self, mock_client_cls):
        # Mock Gemini client response
        mock_response = MagicMock()
        mock_response.text = """
        {
          "title": "Royal Mysuru Exploration",
          "days": [
            {
              "day_number": 1,
              "date": "2026-11-01",
              "destination": "Mysuru",
              "summary": "Immerse in heritage.",
              "stops": [
                {
                  "time": "9:30 AM - 12:30 PM",
                  "name": "Mysuru Palace",
                  "category": "Palace",
                  "meal_type": null,
                  "description": "Grand palace.",
                  "attraction_id": 3,
                  "food_spot_id": null,
                  "source_status": "curated_reference"
                },
                {
                  "time": "1:00 PM - 2:00 PM",
                  "name": "Local Mysuru Thali",
                  "category": "Lunch",
                  "meal_type": "lunch",
                  "description": "Authentic lunch.",
                  "attraction_id": null,
                  "food_spot_id": null,
                  "source_status": "needs_verification"
                },
                {
                  "time": "8:00 PM - 9:00 PM",
                  "name": "Evening Dinner",
                  "category": "Dinner",
                  "meal_type": "dinner",
                  "description": "Delicious dinner.",
                  "attraction_id": null,
                  "food_spot_id": null,
                  "source_status": "needs_verification"
                }
              ]
            }
          ],
          "budget_note": "Within ₹10,000 budget.",
          "weather_note": "Clear skies.",
          "warnings": [],
          "verification_note": "Check palace ticket times."
        }
        """
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        payload = {
            "destinations": ["mysuru"],
            "selected_attraction_ids": [3],
            "start_date": "2026-11-01",
            "end_date": "2026-11-01",
            "traveller_count": 2,
            "travel_style": "comfortable",
            "total_budget": 10000,
            "interests": ["Heritage & culture"],
            "pace": "balanced",
            "profile": {"senior": False},
        }

        res = self.client.post("/api/itineraries/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("gati", data)
        self.assertEqual(data["generation_status"], "ai_generated")
        self.assertEqual(len(data["days"]), 1)
        day1 = data["days"][0]
        self.assertEqual(day1["effort_total"], 35)
        self.assertEqual(day1["stops"][0]["attraction_id"], 3)


if __name__ == "__main__":
    unittest.main()
