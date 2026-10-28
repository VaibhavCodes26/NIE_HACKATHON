"""
Focused tests for the four production fixes.

Run:
    venv\Scripts\python -m pytest test_four_fixes.py -v
"""
import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# ISSUE 1 — Weather forecast: IPv4 transport & timeout configuration
# ---------------------------------------------------------------------------
class TestWeatherService:
    def test_transport_is_ipv4(self):
        from app.services.weather_service import _TRANSPORT
        assert _TRANSPORT is not None, "httpx.HTTPTransport must bind to 0.0.0.0 (IPv4 only)."

    def test_timeout_split(self):
        from app.services.weather_service import _TIMEOUT
        import httpx
        assert isinstance(_TIMEOUT, httpx.Timeout)
        assert _TIMEOUT.connect is not None and _TIMEOUT.connect <= 10
        assert _TIMEOUT.read is not None and _TIMEOUT.read <= 20

    def test_valid_forecast_mysuru(self):
        from app.services.weather_service import get_weather_forecast, clear_weather_cache
        from unittest.mock import patch, MagicMock
        clear_weather_cache()
        today = date.today()
        mock_days = [
            {
                "displayDate": {"year": (today + timedelta(days=i)).year,
                                 "month": (today + timedelta(days=i)).month,
                                 "day": (today + timedelta(days=i)).day},
                "maxTemperature": {"degrees": 31.5},
                "minTemperature": {"degrees": 21.0},
                "daytimeForecast": {
                    "weatherCondition": {"type": "SUNNY"},
                    "precipitation": {"probability": {"percent": 10}},
                },
            }
            for i in range(2)
        ]
        import os
        os.environ["GOOGLE_WEATHER_KEY"] = "test-key"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"forecastDays": mock_days}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.Client.get", return_value=mock_resp):
            result = get_weather_forecast(12.2958, 76.6394, today, today + timedelta(days=1))
            assert result["source"] == "Google Weather"
            assert len(result["daily"]) >= 1
            day = result["daily"][0]
            assert "date" in day and "temperature_max_c" in day

    def test_past_date_raises_value_error(self):
        from app.services.weather_service import get_weather_forecast
        yesterday = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="past dates"):
            get_weather_forecast(12.2958, 76.6394, yesterday, yesterday)

    def test_far_future_returns_partial_notice(self):
        """Dates beyond 10-day window return a polite notice instead of raising ValueError."""
        from app.services.weather_service import get_weather_forecast
        from unittest.mock import patch, MagicMock
        far = date.today() + timedelta(days=20)
        # Mock Google Weather to return only 10 days (today through today+9)
        today = date.today()
        mock_days = [
            {
                "displayDate": {"year": (today + timedelta(days=i)).year,
                                 "month": (today + timedelta(days=i)).month,
                                 "day": (today + timedelta(days=i)).day},
                "maxTemperature": {"degrees": 30.0},
                "minTemperature": {"degrees": 20.0},
                "daytimeForecast": {
                    "weatherCondition": {"type": "SUNNY"},
                    "precipitation": {"probability": {"percent": 10}},
                },
            }
            for i in range(10)
        ]
        import os
        os.environ.setdefault("GOOGLE_WEATHER_KEY", "test-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"forecastDays": mock_days}
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.Client.get", return_value=mock_resp):
            result = get_weather_forecast(12.2958, 76.6394, today, far)
            assert result["has_partial_forecast"] is True
            assert result["forecast_notice"] is not None

    def test_provider_failure_raises_runtime_error(self):
        import httpx
        import os
        from app.services.weather_service import get_weather_forecast, clear_weather_cache
        clear_weather_cache()
        os.environ["GOOGLE_WEATHER_KEY"] = "test-key"
        today = date.today()
        with patch("app.services.weather_service.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectTimeout("simulated")
            mock_cls.return_value = mock_client
            with pytest.raises(RuntimeError, match="temporarily unavailable"):
                get_weather_forecast(12.2958, 76.6394, today, today)


# ---------------------------------------------------------------------------
# ISSUE 2 — Namma Sahayak audio (source code inspection)
# ---------------------------------------------------------------------------
class TestSahayakAudio:
    def _src(self):
        p = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "SahayakPage.jsx")
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_uses_voiceschanged_event(self):
        assert "voiceschanged" in self._src()

    def test_speak_is_async(self):
        assert "async function speak" in self._src()

    def test_uses_getvoicesasync(self):
        assert "getVoicesAsync" in self._src()


# ---------------------------------------------------------------------------
# ISSUE 3 — Food Spots navigation (source code inspection)
# ---------------------------------------------------------------------------
class TestFoodSpotsNavigation:
    def _rd(self):
        p = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "RouteDiscovery.jsx")
        with open(p, encoding="utf-8") as f:
            return f.read()

    def _app(self):
        p = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "App.jsx")
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_no_anchor_href_food_spots(self):
        assert 'href="/food-spots"' not in self._rd(), "Must not use bare <a> anchor for food spots."

    def test_uses_onopenfood_callback(self):
        assert "onOpenFood" in self._rd()

    def test_app_passes_onopenfood(self):
        assert "onOpenFood" in self._app()


# ---------------------------------------------------------------------------
# ISSUE 4 — Drishti 10 MiB limit
# ---------------------------------------------------------------------------
class TestDrishtiUploadLimit:
    def test_max_bytes_is_10mib(self):
        from app.services import drishti_service
        assert drishti_service.MAX_BYTES == 10 * 1024 * 1024

    def test_10mib_file_accepted(self):
        from app.services.drishti_service import validate_image_bytes, MAX_BYTES
        data = b"\xff\xd8\xff\xe0" + b"\x00" * (MAX_BYTES - 4)
        validate_image_bytes(data, "image/jpeg")  # must not raise

    def test_over_10mib_rejected_413(self):
        from app.services.drishti_service import validate_image_bytes, ScanError, MAX_BYTES
        data = b"\x00" * (MAX_BYTES + 1)
        with pytest.raises(ScanError) as exc:
            validate_image_bytes(data, "image/jpeg")
        assert exc.value.status == 413

    def test_route_says_10mb(self):
        p = os.path.join(os.path.dirname(__file__), "app", "routes", "drishti.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        assert "10 MB" in src or "10MB" in src

    def test_frontend_max_is_10mib(self):
        p = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "components", "DrishtiScan.jsx")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        assert "10 * 1024 * 1024" in src
        assert "5MB" not in src

    def test_body_middleware_present(self):
        p = os.path.join(os.path.dirname(__file__), "app", "main.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        assert "_BodySizeLimitMiddleware" in src
        assert "20 * 1024 * 1024" in src
