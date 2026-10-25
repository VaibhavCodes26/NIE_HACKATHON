import io
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_drishti_no_file():
    response = client.post("/api/drishti/translate")
    assert response.status_code == 422  # validation error: missing file
    print("PASS: test_drishti_no_file")

def test_drishti_invalid_mime():
    fake_file = io.BytesIO(b"fake text content")
    response = client.post(
        "/api/drishti/translate",
        files={"file": ("test.txt", fake_file, "text/plain")},
        data={"target_language": "en"}
    )
    assert response.status_code == 400
    assert "Unsupported image format" in response.json().get("detail", "") or "Unsupported image type" in response.json().get("detail", "")
    print("PASS: test_drishti_invalid_mime")

def test_drishti_oversized_file():
    big_file = io.BytesIO(b"x" * (6 * 1024 * 1024))
    response = client.post(
        "/api/drishti/translate",
        files={"file": ("large.jpg", big_file, "image/jpeg")},
        data={"target_language": "en"}
    )
    assert response.status_code == 413
    assert "limit" in response.json().get("detail", "").lower() or "large" in response.json().get("detail", "").lower()
    print("PASS: test_drishti_oversized_file")

def test_drishti_scan_blank_png():
    # 1x1 transparent PNG
    import base64
    png_bytes = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    file_obj = io.BytesIO(png_bytes)
    response = client.post(
        "/api/drishti/translate",
        files={"file": ("blank.png", file_obj, "image/png")},
        data={"target_language": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "detected_text" in data
    assert "translated_text" in data
    assert "target_language" in data
    assert data["source_language"] == "Kannada"
    print("PASS: test_drishti_scan_blank_png, response:", data)

if __name__ == "__main__":
    test_drishti_no_file()
    test_drishti_invalid_mime()
    test_drishti_oversized_file()
    test_drishti_scan_blank_png()
    print("\nALL DRISHTI TESTS PASSED!")
