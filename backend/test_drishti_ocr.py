import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def generate_kannada_sign():
    img = Image.new("RGB", (600, 250), color=(245, 230, 180))
    draw = ImageDraw.Draw(img)
    # Draw yellow-red border
    draw.rectangle([10, 10, 590, 240], outline=(169, 31, 36), width=5)
    
    # Try loading a font that supports Kannada on Windows, like Nirmala.ttf
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\Nirmala.ttf", 36)
        font_sub = ImageFont.truetype("C:\\Windows\\Fonts\\Nirmala.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((60, 40), "ಸ್ವಾಗತ - ಮೈಸೂರು ಅರಮನೆ", fill=(169, 31, 36), font=font)
    draw.text((60, 110), "ಪ್ರವೇಶ ದ್ವಾರ", fill=(20, 20, 20), font=font)
    draw.text((60, 170), "Welcome to Mysore Palace - Entrance", fill=(60, 60, 60), font=font_sub)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf.getvalue()

def test_signboard_translation():
    img_bytes = generate_kannada_sign()
    
    # Test English translation
    resp = client.post(
        "/api/drishti/translate",
        files={"file": ("signboard.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"target_language": "en"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    print("EN Response:", data)
    assert data["success"] is True
    assert "ಮೈಸೂರು" in data["detected_text"] or "ಸ್ವಾಗತ" in data["detected_text"] or "Mysore" in data["translated_text"] or "Palace" in data["translated_text"]

    # Test Hindi translation & cache test
    resp_hi = client.post(
        "/api/drishti/translate",
        files={"file": ("signboard.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"target_language": "hi"}
    )
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    print("HI Response:", data_hi)
    assert data_hi["success"] is True
    assert data_hi["target_language"] == "Hindi"

    # Test re-request for English -> should be cached
    resp_cached = client.post(
        "/api/drishti/translate",
        files={"file": ("signboard.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"target_language": "en"}
    )
    assert resp_cached.status_code == 200
    data_cached = resp_cached.json()
    assert data_cached.get("cached") is True
    print("Cached check PASS! cached=True")

if __name__ == "__main__":
    test_signboard_translation()
    print("SIGNBOARD OCR & TRANSLATION TEST PASSED!")
