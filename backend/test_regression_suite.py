"""
Comprehensive regression test suite for Namma Gati itinerary planning.
Verifies all 13 required test cases:
1. Mysuru Palace is selected and appears as an actual scheduled activity.
2. Multiple selected attractions are all scheduled when feasible.
3. Effort-point differences do not silently eliminate selected attractions.
4. Senior-citizen preference changes the actual schedule appropriately.
5. Pregnancy preference prevents normal scheduling of activities explicitly classified as unsuitable or strenuous, while uncertain suitability is flagged rather than assumed.
6. Less-walking and mobility preferences affect activity selection, duration, transport, and pacing where data supports those decisions.
7. Avoid-strenuous-treks excludes activities classified as strenuous.
8. Less-rainy preference uses actual available weather data to adjust suitable activities without silently discarding mandatory selections.
9. Multi-city trips preserve selected attractions and preferences across every city.
10. Too many selected attractions produce an explicit unscheduled list and explanation.
11. Gemini omitting a selected attraction is detected by the final integrity check.
12. Missing weather or accessibility data does not cause fabricated claims.
13. One-city itineraries continue to work.
"""
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import gati_service
from app.services.gemini_service import _validate_and_enforce_daily_structure


class TestNammaGatiRegressionSuite(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # -------------------------------------------------------------------------
    # Case 1: Mysuru Palace is selected and appears as an actual scheduled activity.
    # -------------------------------------------------------------------------
    def test_case_1_mysuru_palace_scheduled(self):
        stops = [
            {"id": 3, "name": "Mysuru Palace", "city": "Mysuru", "category": "Palace", "estimated_duration_minutes": 120, "is_must_visit": True},
            {"id": 27, "name": "Chamundi Hills", "city": "Mysuru", "category": "Hills", "estimated_duration_minutes": 120},
            {"id": 4, "name": "Devaraja Market", "city": "Mysuru", "category": "Market", "estimated_duration_minutes": 90},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Mysuru"],
            selected_attraction_ids=[3, 27],
            pace="balanced"
        )
        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertIn(3, scheduled_ids, "Mysuru Palace must be scheduled when selected")
        self.assertIn(27, scheduled_ids, "Chamundi Hills must be scheduled when selected")

    # -------------------------------------------------------------------------
    # Case 2: Multiple selected attractions are all scheduled when feasible.
    # -------------------------------------------------------------------------
    def test_case_2_multiple_selected_attractions_all_scheduled(self):
        stops = [
            {"id": 3, "name": "Mysuru Palace", "city": "Mysuru", "category": "Palace"},
            {"id": 28, "name": "Jaganmohan Palace Art Gallery", "city": "Mysuru", "category": "Art Gallery"},
            {"id": 29, "name": "St. Philomena's Cathedral", "city": "Mysuru", "category": "Church"},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Mysuru"],
            selected_attraction_ids=[3, 28, 29],
            pace="balanced"
        )
        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertEqual(set(scheduled_ids), {3, 28, 29}, "All three feasible selections must be scheduled")
        self.assertEqual(len(res["deferred"]), 0, "No feasible selections should be deferred")

    # -------------------------------------------------------------------------
    # Case 3: Effort-point differences do not silently eliminate selected attractions.
    # -------------------------------------------------------------------------
    def test_case_3_effort_point_differences_do_not_silently_eliminate(self):
        # Chamundi Hill Steps Trek has high effort (70 pts). Mysuru Palace has 30 pts.
        # Previously, sorting by descending effort pushed Mysuru Palace out.
        stops = [
            {"id": 50, "name": "Chamundi Hill Steps Trek", "city": "Mysuru", "category": "Trek"}, # 70 pts
            {"id": 3, "name": "Mysuru Palace", "city": "Mysuru", "category": "Palace", "is_must_visit": True}, # 30 pts
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Mysuru"],
            selected_attraction_ids=[50, 3],
            pace="balanced"
        )
        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertIn(3, scheduled_ids, "Lower-effort Mysuru Palace must not be eliminated by higher effort stop")
        self.assertIn(50, scheduled_ids)

    # -------------------------------------------------------------------------
    # Case 4: Senior-citizen preference changes the actual schedule appropriately.
    # -------------------------------------------------------------------------
    def test_case_4_senior_citizen_preference_changes_schedule(self):
        stops = [
            {"id": 3, "name": "Mysuru Palace", "city": "Mysuru", "category": "Palace", "estimated_duration_minutes": 120},
            {"id": 27, "name": "Chamundi Hills", "city": "Mysuru", "category": "Hills", "estimated_duration_minutes": 120},
            {"id": 101, "name": "Kudremukh Peak Trek", "city": "Mysuru", "category": "Trek", "estimated_duration_minutes": 240},
        ]
        res_standard = gati_service.plan(stops=stops, n_days=2, cities=["Mysuru"], profile={"senior": False})
        res_senior = gati_service.plan(stops=stops, n_days=2, cities=["Mysuru"], profile={"senior": True})

        # Capacity is lower for senior group (77 vs 110)
        self.assertLess(res_senior["summary"]["capacity"], res_standard["summary"]["capacity"])
        # Kudremukh (85 effort) is deferred for senior group as too strenuous
        senior_deferred_codes = [x["code"] for x in res_senior["deferred"]]
        self.assertIn("strenuous", senior_deferred_codes)
        # Senior notes are injected into schedule
        all_notes = " ".join(n for d in res_senior["days"] for n in d["notes"])
        self.assertIn("senior citizens", all_notes.lower())

    # -------------------------------------------------------------------------
    # Case 5: Pregnancy preference prevents normal scheduling of unsuitable/strenuous,
    #         and flags uncertain suitability rather than assuming safety.
    # -------------------------------------------------------------------------
    def test_case_5_pregnancy_preference_handling(self):
        stops = [
            {"id": 201, "name": "Savandurga Rock Climb", "city": "Bengaluru", "category": "Adventure Climb", "effort": 80},
            {"id": 202, "name": "Chitradurga Fort Steps", "city": "Chitradurga", "category": "Fort", "effort": 45},
            {"id": 203, "name": "Bengaluru Museum of Art", "city": "Bengaluru", "category": "Museum", "effort": 20},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=2,
            cities=["Bengaluru", "Chitradurga"],
            profile={"pregnant": True},
            selected_attraction_ids=[201, 202, 203]
        )
        # Strenuous rock climb must be excluded with unsuitable_pregnancy
        deferred_codes = [x["code"] for x in res["deferred"]]
        self.assertIn("unsuitable_pregnancy", deferred_codes)
        deferred_ids = [x["id"] for x in res["deferred"]]
        self.assertIn(201, deferred_ids)

        # Fort with stairs must be scheduled but flagged with suitability_uncertain
        day_stops = [s for d in res["days"] for s in d["stops"]]
        fort_stop = next((s for s in day_stops if s["id"] == 202), None)
        self.assertIsNotNone(fort_stop)
        self.assertEqual(fort_stop.get("safety_flag"), "suitability_uncertain")
        self.assertIn("cannot be established reliably", fort_stop.get("safety_note", ""))

        # Mild museum has no safety impediment
        museum_stop = next((s for s in day_stops if s["id"] == 203), None)
        self.assertIsNotNone(museum_stop)
        self.assertIsNone(museum_stop.get("safety_flag"))

    # -------------------------------------------------------------------------
    # Case 6: Less-walking and mobility preferences affect activity selection, duration, pacing.
    # -------------------------------------------------------------------------
    def test_case_6_less_walking_and_mobility_preferences(self):
        stops = [
            {"id": 301, "name": "Badami Cave Temples", "city": "Badami", "category": "Cave temple", "effort": 45},
            {"id": 302, "name": "Archaeological Museum Badami", "city": "Badami", "category": "Museum", "effort": 20},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Badami"],
            profile={"mobility": True, "less_walking": True},
            pace="less-walking",
            selected_attraction_ids=[301, 302]
        )
        # Reduced max_stops to enforce easy walking pace
        self.assertLessEqual(res["summary"]["max_stops"], 3)
        # Cave temple with uneven ground/steps flagged for mobility
        day_stops = [s for d in res["days"] for s in d["stops"]]
        cave_stop = next((s for s in day_stops if s["id"] == 301), None)
        self.assertIsNotNone(cave_stop)
        self.assertEqual(cave_stop.get("accessibility_flag"), "accessibility_uncertain")
        self.assertIn("steps or uneven paving", cave_stop.get("accessibility_note", ""))
        # Pacing notes mention less walking or mobility
        all_notes = " ".join(n for d in res["days"] for n in d["notes"])
        self.assertTrue("less walking" in all_notes.lower() or "mobility" in all_notes.lower())

    # -------------------------------------------------------------------------
    # Case 7: Avoid-strenuous-treks excludes activities classified as strenuous.
    # -------------------------------------------------------------------------
    def test_case_7_avoid_strenuous_treks_excludes_treks(self):
        stops = [
            {"id": 401, "name": "Kumara Parvatha Trek", "city": "Coorg", "category": "Adventure Trek", "effort": 90},
            {"id": 402, "name": "Madikeri Fort", "city": "Coorg", "category": "Fort", "effort": 40},
            {"id": 403, "name": "Raja's Seat Viewpoint", "city": "Coorg", "category": "Viewpoint", "effort": 15},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Coorg"],
            profile={"avoid_strenuous": True},
            selected_attraction_ids=[401, 402, 403]
        )
        deferred_codes = [x["code"] for x in res["deferred"]]
        self.assertIn("avoid_strenuous", deferred_codes)
        deferred_ids = [x["id"] for x in res["deferred"]]
        self.assertIn(401, deferred_ids, "Kumara Parvatha Trek must be excluded")

        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertNotIn(401, scheduled_ids)
        self.assertIn(402, scheduled_ids)
        self.assertIn(403, scheduled_ids)

    # -------------------------------------------------------------------------
    # Case 8: Less-rainy preference uses actual available weather data without discarding mandatory stops.
    # -------------------------------------------------------------------------
    def test_case_8_less_rainy_preference_with_weather_data(self):
        stops = [
            {"id": 501, "name": "Abbey Falls", "city": "Coorg", "category": "Waterfall", "effort": 50},
            {"id": 502, "name": "Coffee Museum", "city": "Coorg", "category": "Museum", "effort": 20},
        ]
        mock_weather = [
            {
                "destination": "Coorg",
                "date": "2026-11-01",
                "precipitation_probability_max": 75,
                "temperature_max_c": 24,
                "weather_code": 61,
            }
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Coorg"],
            start_date="2026-11-01",
            profile={"rain_friendly": True},
            selected_attraction_ids=[501, 502],
            weather_data=mock_weather
        )
        # Mandatory outdoor stop (Abbey Falls) is NOT dropped
        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertIn(501, scheduled_ids, "Outdoor mandatory stop must not be dropped due to rain")
        self.assertIn(502, scheduled_ids)

        # Outdoor stop has a weather advisory note
        falls_stop = next((s for s in res["days"][0]["stops"] if s["id"] == 501), None)
        self.assertIsNotNone(falls_stop.get("weather_note"))
        self.assertIn("75%", falls_stop["weather_note"])

        # Indoor stop marked as sheltered
        museum_stop = next((s for s in res["days"][0]["stops"] if s["id"] == 502), None)
        self.assertIn("sheltered", museum_stop.get("weather_note", "").lower())

    # -------------------------------------------------------------------------
    # Case 9: Multi-city trips preserve selected attractions and preferences across every city.
    # -------------------------------------------------------------------------
    def test_case_9_multi_city_trips_preserve_selections_across_cities(self):
        stops = [
            {"id": 1, "name": "Bangalore Palace", "city": "Bengaluru", "category": "Palace", "is_must_visit": True},
            {"id": 3, "name": "Mysuru Palace", "city": "Mysuru", "category": "Palace", "is_must_visit": True},
            {"id": 5, "name": "Virupaksha Temple", "city": "Hampi", "category": "Temple", "is_must_visit": True},
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=3,
            cities=["Bengaluru", "Mysuru", "Hampi"],
            selected_attraction_ids=[1, 3, 5],
            profile={"senior": True}
        )
        scheduled_ids = [s["id"] for d in res["days"] for s in d["stops"]]
        self.assertIn(1, scheduled_ids, "Bengaluru Palace must be scheduled")
        self.assertIn(3, scheduled_ids, "Mysuru Palace must be scheduled")
        self.assertIn(5, scheduled_ids, "Hampi Virupaksha Temple must be scheduled")

        # Each day covers the corresponding city
        self.assertEqual(res["days"][0]["cities"], ["Bengaluru"])
        self.assertEqual(res["days"][1]["cities"], ["Mysuru"])
        self.assertEqual(res["days"][2]["cities"], ["Hampi"])

    # -------------------------------------------------------------------------
    # Case 10: Too many selected attractions produce an explicit unscheduled list and explanation.
    # -------------------------------------------------------------------------
    def test_case_10_too_many_selected_attractions_produce_explicit_unscheduled(self):
        # 8 mandatory stops packed into 1 day
        stops = [
            {"id": i, "name": f"Mysuru Attraction {i}", "city": "Mysuru", "category": "Temple", "effort": 35}
            for i in range(1, 9)
        ]
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Mysuru"],
            selected_attraction_ids=list(range(1, 9))
        )
        self.assertGreater(len(res["deferred"]), 0, "Overloaded day must produce deferred items")
        self.assertGreater(len(res["unscheduled"]), 0, "Unscheduled list must be populated")
        for item in res["unscheduled"]:
            self.assertEqual(item["code"], "no_room")
            self.assertTrue("adding a day" in item["reason"].lower() or "add a day" in item["reason"].lower())

    # -------------------------------------------------------------------------
    # Case 11: Gemini omitting a selected attraction is detected by the final integrity check.
    # -------------------------------------------------------------------------
    def test_case_11_gemini_omission_detected_and_restored(self):
        # Simulate Gati having scheduled Mysuru Palace (id: 3), but Gemini returned only meals and no stops
        mock_gati_plan = {
            "days": [
                {
                    "day": 1,
                    "day_number": 1,
                    "destination": "Mysuru",
                    "cities": ["Mysuru"],
                    "stops": [
                        {"id": 3, "name": "Mysuru Palace", "category": "Palace", "effort": 30, "level": "medium", "suggested_time": "Morning", "is_mandatory": True}
                    ],
                    "total": 30,
                    "capacity": 110,
                    "status": "ok",
                    "notes": []
                }
            ],
            "deferred": [],
            "warnings": []
        }
        mock_gemini_output = {
            "title": "Mysuru Trip",
            "days": [
                {
                    "day_number": 1,
                    "destination": "Mysuru",
                    "stops": [
                        # Gemini omitted Mysuru Palace!
                        {"name": "Local Lunch", "meal_type": "lunch", "category": "Lunch", "attraction_id": None},
                        {"name": "Local Dinner", "meal_type": "dinner", "category": "Dinner", "attraction_id": None},
                    ]
                }
            ],
            "warnings": []
        }
        enforced = _validate_and_enforce_daily_structure(
            result=mock_gemini_output,
            destinations=["Mysuru"],
            attractions=[{"id": 3, "name": "Mysuru Palace", "category": "Palace", "effort": 30}],
            food_spots=[],
            gati_plan=mock_gati_plan,
            selected_attraction_ids=[3]
        )
        scheduled_attr_ids = [s.get("attraction_id") for s in enforced["days"][0]["stops"]]
        self.assertIn(3, scheduled_attr_ids, "Integrity check must restore dropped Mysuru Palace")

    # -------------------------------------------------------------------------
    # Case 12: Missing weather or accessibility data does not cause fabricated claims.
    # -------------------------------------------------------------------------
    def test_case_12_missing_weather_or_accessibility_not_fabricated(self):
        stops = [
            {"id": 601, "name": "Lalbagh Botanical Garden", "city": "Bengaluru", "category": "Garden", "effort": 25}
        ]
        # No weather data provided
        res = gati_service.plan(
            stops=stops,
            n_days=1,
            cities=["Bengaluru"],
            weather_data=None,
            selected_attraction_ids=[601]
        )
        lalbagh = res["days"][0]["stops"][0]
        # Weather note should not fabricate rain or temperature claims
        self.assertIsNone(lalbagh.get("weather_note"))
        # Accessibility note not fabricated when not indicated
        self.assertIsNone(lalbagh.get("accessibility_flag"))

    # -------------------------------------------------------------------------
    # Case 13: One-city itineraries continue to work via API endpoint.
    # -------------------------------------------------------------------------
    @patch("app.main.get_weather_forecast")
    def test_case_13_one_city_itinerary_preview_endpoint(self, mock_weather):
        mock_weather.return_value = {
            "daily": [{"date": "2026-11-01", "precipitation_probability_max": 10, "temperature_2m_max": 28, "temperature_2m_min": 19, "weather_code": 1}]
        }
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
        res = self.client.post("/api/itineraries/preview", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "preview")
        self.assertEqual(len(data["days"]), 1)
        day1_stops = data["days"][0]["stops"]
        self.assertTrue(any(s["attraction_id"] == 3 for s in day1_stops), "Mysuru Palace must be present in preview")


if __name__ == "__main__":
    unittest.main()
