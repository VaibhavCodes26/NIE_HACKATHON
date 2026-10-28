"""Kannada Text-to-Speech service with multi-provider fallback and caching."""

import base64
import hashlib
import logging
import os
import threading
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Cache directory under backend/app/data/tts_cache
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TTS_CACHE_DIR = DATA_DIR / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory audio cache: sha256_hash -> bytes
_TTS_MEMORY_CACHE: dict[str, bytes] = {}
_CACHE_LOCK = threading.Lock()

# Deduplication for simultaneous requests
_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT_EVENTS: dict[str, threading.Event] = {}

# Timeouts for upstream TTS providers
_TTS_TIMEOUT = httpx.Timeout(connect=6.0, read=12.0, write=5.0, pool=5.0)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def clear_tts_cache(memory_only: bool = True):
    """Clear the TTS memory cache (used in unit tests)."""
    with _CACHE_LOCK:
        _TTS_MEMORY_CACHE.clear()
    with _INFLIGHT_LOCK:
        _INFLIGHT_EVENTS.clear()


def _clean_text(text: str) -> str:
    """Normalize Kannada text for TTS synthesis."""
    if not text:
        return ""
    cleaned = text.replace("…", " ").replace("...", " ").strip()
    return " ".join(cleaned.split())


def _get_cache_key(text: str) -> str:
    """Compute sha256 digest of normalized text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_google_cloud_tts(text: str, api_key: str) -> bytes:
    """Synthesize speech using official Google Cloud Text-to-Speech API."""
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": "kn-IN",
            "name": "kn-IN-Standard-A",
            "ssmlGender": "FEMALE",
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.9,
        },
    }
    with httpx.Client(timeout=_TTS_TIMEOUT) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        audio_content = data.get("audioContent")
        if not audio_content:
            raise RuntimeError("Google Cloud TTS returned empty audioContent.")
        return base64.b64decode(audio_content)


def _fetch_google_translate_tts(text: str) -> bytes:
    """Synthesize speech using Google Translate Kannada TTS endpoint (zero-config)."""
    url = "https://translate.google.com/translate_tts"
    params = {
        "ie": "UTF-8",
        "q": text,
        "tl": "kn",
        "client": "tw-ob",
    }
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=_TTS_TIMEOUT) as client:
        response = client.get(url, params=params, headers=headers)
        response.raise_for_status()
        content = response.content
        if len(content) < 100:
            raise RuntimeError("Google Translate TTS returned suspiciously small payload.")
        return content


def synthesize_kannada_speech(text: str) -> bytes:
    """Return MP3 audio bytes for the given Kannada phrase.

    Uses a tiered architecture:
    1. Check memory cache (instant).
    2. Check persistent disk cache (instant).
    3. Deduplicate in-flight requests for identical phrases.
    4. Primary provider: Google Cloud Text-to-Speech API (if GOOGLE_TTS_API_KEY is configured).
    5. Fallback/Default provider: Google Translate Kannada TTS.
    6. Persist generated audio to disk and memory caches.
    """
    cleaned = _clean_text(text)
    if not cleaned:
        raise ValueError("Text to synthesize cannot be empty.")

    if len(cleaned) > 500:
        raise ValueError("Text exceeds maximum synthesis length of 500 characters.")

    cache_key = _get_cache_key(cleaned)

    # 1. Check in-memory cache
    with _CACHE_LOCK:
        if cache_key in _TTS_MEMORY_CACHE:
            return _TTS_MEMORY_CACHE[cache_key]

    # 2. Check disk cache
    cached_file = TTS_CACHE_DIR / f"{cache_key}.mp3"
    if cached_file.exists():
        try:
            audio_bytes = cached_file.read_bytes()
            if len(audio_bytes) > 0:
                with _CACHE_LOCK:
                    _TTS_MEMORY_CACHE[cache_key] = audio_bytes
                return audio_bytes
        except Exception as read_err:
            logger.warning("[tts] Failed to read disk cache for %s: %s", cache_key, read_err)

    # 3. Deduplicate simultaneous in-flight requests
    my_event = None
    with _INFLIGHT_LOCK:
        if cache_key in _INFLIGHT_EVENTS:
            waiting_event = _INFLIGHT_EVENTS[cache_key]
        else:
            waiting_event = None
            my_event = threading.Event()
            _INFLIGHT_EVENTS[cache_key] = my_event

    if waiting_event is not None:
        waiting_event.wait(timeout=15.0)
        with _CACHE_LOCK:
            if cache_key in _TTS_MEMORY_CACHE:
                return _TTS_MEMORY_CACHE[cache_key]
        if cached_file.exists():
            try:
                return cached_file.read_bytes()
            except Exception:
                pass

    # 4. Fetch from TTS providers
    audio_bytes: bytes | None = None
    last_error: Exception | None = None

    try:
        # Check if Google Cloud TTS API key is provided
        cloud_key = os.getenv("GOOGLE_TTS_API_KEY", "").strip()
        if cloud_key:
            try:
                audio_bytes = _fetch_google_cloud_tts(cleaned, cloud_key)
            except Exception as exc:
                last_error = exc
                logger.warning("[tts] Google Cloud TTS failed, falling back to Translate TTS: %s", exc)

        # Fallback or zero-config: Google Translate TTS
        if audio_bytes is None:
            try:
                audio_bytes = _fetch_google_translate_tts(cleaned)
            except Exception as exc:
                last_error = exc
                logger.error("[tts] Google Translate TTS failed: %s", exc)

        if audio_bytes is None:
            raise RuntimeError("Kannada speech synthesis failed from all providers.") from last_error

        # 5. Persist to cache
        with _CACHE_LOCK:
            _TTS_MEMORY_CACHE[cache_key] = audio_bytes

        try:
            cached_file.write_bytes(audio_bytes)
        except Exception as write_err:
            logger.warning("[tts] Failed to write disk cache for %s: %s", cache_key, write_err)

        return audio_bytes

    finally:
        if my_event is not None:
            my_event.set()
            with _INFLIGHT_LOCK:
                _INFLIGHT_EVENTS.pop(cache_key, None)
