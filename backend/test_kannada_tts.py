"""Unit tests for Namma Sahayak Kannada Text-to-Speech (TTS) service and route.

All upstream provider calls are mocked to prevent consuming network quota.
"""

import base64
import os
import shutil
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.tts_service import (
    TTS_CACHE_DIR,
    clear_tts_cache,
    synthesize_kannada_speech,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure tests run with an empty in-memory and disk cache."""
    clear_tts_cache()
    if TTS_CACHE_DIR.exists():
        for f in TTS_CACHE_DIR.glob("*.mp3"):
            try:
                f.unlink()
            except Exception:
                pass
    yield
    clear_tts_cache()


def _mock_translate_tts_response(status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    if status_code == 200:
        resp.content = b"\xff\xf3\x84\x00" + b"\x11" * 1024
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _mock_cloud_tts_response(status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    if status_code == 200:
        fake_audio = b"\xff\xf3\x84\x00" + b"\x22" * 1024
        resp.json.return_value = {"audioContent": base64.b64encode(fake_audio).decode("ascii")}
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_synthesize_kannada_speech_success(monkeypatch):
    """Test successful speech synthesis using mocked Google Translate TTS."""
    monkeypatch.delenv("GOOGLE_TTS_API_KEY", raising=False)
    mock_resp = _mock_translate_tts_response(200)

    with patch("app.services.tts_service.httpx.Client.get", return_value=mock_resp) as mock_get:
        audio = synthesize_kannada_speech("ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ")
        assert len(audio) > 100
        assert audio.startswith(b"\xff\xf3")
        assert mock_get.call_count == 1


def test_tts_in_memory_and_disk_caching(monkeypatch):
    """Test that repeated calls for identical phrases return cached audio without calling upstream."""
    monkeypatch.delenv("GOOGLE_TTS_API_KEY", raising=False)
    mock_resp = _mock_translate_tts_response(200)

    with patch("app.services.tts_service.httpx.Client.get", return_value=mock_resp) as mock_get:
        audio1 = synthesize_kannada_speech("ನಮಸ್ಕಾರ ಪರೀಕ್ಷೆ")
        assert mock_get.call_count == 1

        # Second call must be served from cache
        audio2 = synthesize_kannada_speech("ನಮಸ್ಕಾರ ಪರೀಕ್ಷೆ")
        assert audio1 == audio2
        assert mock_get.call_count == 1  # No second HTTP call


def test_google_cloud_tts_primary_when_key_present(monkeypatch):
    """Verify Google Cloud TTS is called when GOOGLE_TTS_API_KEY is configured."""
    monkeypatch.setenv("GOOGLE_TTS_API_KEY", "test-cloud-tts-key")
    cloud_resp = _mock_cloud_tts_response(200)

    with patch("app.services.tts_service.httpx.Client.post", return_value=cloud_resp) as mock_post:
        with patch("app.services.tts_service.httpx.Client.get") as mock_get:
            audio = synthesize_kannada_speech("ಧನ್ಯವಾದಗಳು")
            assert len(audio) > 100
            assert mock_post.call_count == 1
            assert mock_get.call_count == 0  # Fallback not needed


def test_google_cloud_tts_fails_falls_back_to_translate(monkeypatch):
    """Verify fallback to Translate TTS when Google Cloud TTS returns error."""
    monkeypatch.setenv("GOOGLE_TTS_API_KEY", "test-cloud-tts-key")
    cloud_500 = _mock_cloud_tts_response(500)
    translate_200 = _mock_translate_tts_response(200)

    with patch("app.services.tts_service.httpx.Client.post", return_value=cloud_500):
        with patch("app.services.tts_service.httpx.Client.get", return_value=translate_200) as mock_get:
            audio = synthesize_kannada_speech("ಶುಭ ದಿನ")
            assert len(audio) > 100
            assert mock_get.call_count == 1


def test_empty_or_too_long_text_validation():
    """Verify ValueError is raised on empty text or text exceeding 500 characters."""
    with pytest.raises(ValueError, match="cannot be empty"):
        synthesize_kannada_speech("   ")

    with pytest.raises(ValueError, match="exceeds maximum synthesis length"):
        synthesize_kannada_speech("ಅ" * 501)


def test_simultaneous_tts_deduplication():
    """Verify concurrent requests for the same phrase share a single upstream call."""
    mock_resp = _mock_translate_tts_response(200)
    call_counter = 0

    def slow_get(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        time.sleep(0.1)
        return mock_resp

    results = []

    def worker():
        audio = synthesize_kannada_speech("ಹೌದು ಖಂಡಿತ")
        results.append(audio)

    with patch("app.services.tts_service.httpx.Client.get", side_effect=slow_get):
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(results) == 5
    assert call_counter == 1


def test_tts_api_endpoint():
    """Verify GET /api/sahayak/tts returns 200 OK, audio/mpeg, and Cache-Control headers."""
    client = TestClient(app)
    mock_audio = b"\xff\xf3\x84\x00" + b"\x55" * 1024

    with patch("app.routes.sahayak.tts_service.synthesize_kannada_speech", return_value=mock_audio):
        response = client.get("/api/sahayak/tts", params={"text": "ನಮಸ್ಕಾರ"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert "public" in response.headers["cache-control"]
        assert len(response.content) == len(mock_audio)


def test_tts_api_endpoint_503_on_failure(monkeypatch):
    """Verify GET /api/sahayak/tts returns 503 when providers fail."""
    client = TestClient(app)

    with patch("app.routes.sahayak.tts_service.synthesize_kannada_speech", side_effect=RuntimeError("Provider failure")):
        response = client.get("/api/sahayak/tts", params={"text": "ಹಲೋ"})
        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data["detail"].lower()


def test_frontend_source_compliance():
    """Verify frontend SahayakPage.jsx integrates backend TTS endpoint with graceful fallback."""
    sahayak_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "SahayakPage.jsx")
    with open(sahayak_path, encoding="utf-8") as f:
        src = f.read()

    # Must call the backend TTS endpoint
    assert "/api/sahayak/tts" in src
    # Must use HTML5 Audio
    assert "new Audio(" in src
    # Must retain getVoicesAsync and voiceschanged for fallback and existing test compatibility
    assert "getVoicesAsync" in src
    assert "voiceschanged" in src
    assert "async function speak" in src
    # Must never claim English or non-Kannada voice is Kannada
    assert "browser will use its default voice" not in src
