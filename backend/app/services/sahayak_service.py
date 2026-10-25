"""
Namma Sahayak RAG service.

Key design rule: Gemini NEVER writes Kannada. It only chooses phrase IDs from
the verified phrasebook and explains them in the user's language. The Kannada
text shown in the UI always comes from sahayak_kb.json.
"""
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import numpy as np
from google import genai
from google.genai import types

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KB_PATH = DATA_DIR / "sahayak_kb.json"
EMB_CACHE = DATA_DIR / "sahayak_kb.emb.npz"

GEN_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
EMB_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

LANG_NAME = {"en": "English", "hi": "Hindi (Devanagari script)", "mr": "Marathi (Devanagari script)"}

# ---------- load knowledge base ----------
_KB = json.loads(KB_PATH.read_text(encoding="utf-8"))
PHRASES = {p["id"]: p for p in _KB["phrases"]}
TIPS = {t["id"]: t for t in _KB["tips"]}
SCENARIOS = _KB["scenarios"]

# one list of retrievable docs: phrases and tips
DOCS = [
    {"id": p["id"], "kind": "phrase", "scenario": p["scenario"], "text": f'{p["scenario"]}: {p["en"]}'}
    for p in _KB["phrases"]
] + [
    {"id": t["id"], "kind": "tip", "scenario": t["scenario"], "text": f'{t["scenario"]}: {t["en"]}'}
    for t in _KB["tips"]
]

# ---------- embeddings ----------
def _embed(texts: list[str]) -> np.ndarray:
    out = []
    for i in range(0, len(texts), 90):  # API batch limit safety
        res = _client.models.embed_content(model=EMB_MODEL, contents=texts[i:i + 90])
        out.extend([e.values for e in res.embeddings])
    arr = np.array(out, dtype="float32")
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)


def _load_doc_vectors() -> Optional[np.ndarray]:
    sig = hashlib.md5(json.dumps(DOCS, sort_keys=True).encode()).hexdigest()
    if EMB_CACHE.exists():
        cached = np.load(EMB_CACHE, allow_pickle=False)
        if str(cached["sig"]) == sig:
            return cached["vecs"]
    try:
        vecs = _embed([d["text"] for d in DOCS])
        np.savez(EMB_CACHE, vecs=vecs, sig=sig)
        return vecs
    except Exception as e:  # no network / quota: fall back to keyword search
        print("[sahayak] embedding failed, using keyword fallback:", e)
        return None


_DOC_VECS = _load_doc_vectors()


def _keyword_scores(query: str) -> np.ndarray:
    q = set(re.findall(r"\w+", query.lower()))
    return np.array([len(q & set(re.findall(r"\w+", d["text"].lower()))) for d in DOCS], dtype="float32")


def retrieve(query: str, scenario: Optional[str], k_phrases=6, k_tips=3):
    try:
        if _DOC_VECS is None:
            raise RuntimeError("no vectors")
        qv = _embed([query])[0]
        scores = _DOC_VECS @ qv
    except Exception:
        scores = _keyword_scores(query)
    if scenario:  # soft boost if the user tapped a scenario card
        scores = scores + np.array([0.15 if d["scenario"] == scenario else 0 for d in DOCS], dtype="float32")
    order = np.argsort(-scores)
    phrases, tips = [], []
    for i in order:
        d = DOCS[i]
        if d["kind"] == "phrase" and len(phrases) < k_phrases:
            phrases.append(PHRASES[d["id"]])
        elif d["kind"] == "tip" and len(tips) < k_tips:
            tips.append(TIPS[d["id"]])
        if len(phrases) >= k_phrases and len(tips) >= k_tips:
            break
    return phrases, tips


# ---------- generation ----------
SYSTEM = """You are Namma Sahayak, a friendly travel helper for tourists in Karnataka, India.
RULES:
1. You may ONLY recommend phrases whose id appears in PHRASES. Never invent or write Kannada yourself.
2. Write 'answer', 'meaning' and 'tips' in the requested USER LANGUAGE, simple and short.
3. Use TIPS for etiquette/bargaining advice; do not invent prices or laws. If the user wants a fair price, tell them to check the route planner estimate.
4. If no phrase fits, return an empty phrases list and say so honestly.
5. Return ONLY JSON: {"answer": str, "phrases": [{"id": str, "meaning": str}], "tips": [str], "show_to_local_id": str|null}
   Pick at most 5 phrases, in the order the user should say them. show_to_local_id is the single most useful phrase to show on screen."""


def _cache_key(*parts) -> str:
    return hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()


_CACHE: dict[str, dict] = {}


def _hydrate(ids_meanings, language):
    out = []
    for item in ids_meanings:
        p = PHRASES.get(item.get("id"))
        if p:  # drop anything the model made up
            out.append({
                "id": p["id"], "kn": p["kn"], "roman": p["roman"], "deva": p["deva"],
                "en": p["en"], "meaning": item.get("meaning") or p["en"],
            })
    return out


def ask(query: str, language: str = "en", scenario: Optional[str] = None, context: Optional[dict] = None) -> dict:
    key = _cache_key(query.strip().lower(), language, scenario, json.dumps(context or {}, sort_keys=True))
    if key in _CACHE:
        return _CACHE[key]

    phrases, tips = retrieve(query, scenario)

    # --- fallback result if Gemini fails (demo-proof) ---
    fallback = {
        "answer": "Here are phrases that match your situation." if language == "en"
        else "आपकी स्थिति के हिसाब से ये वाक्य काम आएँगे।",
        "phrases": _hydrate([{"id": p["id"]} for p in phrases[:5]], language),
        "tips": [t["en"] for t in tips[:2]],
        "show_to_local_id": phrases[0]["id"] if phrases else None,
        "source": "fallback",
    }

    prompt = {
        "USER LANGUAGE": LANG_NAME.get(language, "English"),
        "USER QUESTION": query,
        "TRIP CONTEXT": context or {},
        "PHRASES": [{"id": p["id"], "scenario": p["scenario"], "english": p["en"]} for p in phrases],
        "TIPS": [t["en"] for t in tips],
    }
    try:
        res = _client.models.generate_content(
            model=GEN_MODEL,
            contents=json.dumps(prompt, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        data = json.loads(res.text)
        result = {
            "answer": str(data.get("answer", "")),
            "phrases": _hydrate(data.get("phrases", []), language),
            "tips": [str(t) for t in data.get("tips", [])][:3],
            "show_to_local_id": data.get("show_to_local_id") if data.get("show_to_local_id") in PHRASES else None,
            "source": "gemini",
        }
        if not result["phrases"] and phrases:  # model returned nothing usable
            result["phrases"] = fallback["phrases"]
        _CACHE[key] = result
        return result
    except Exception as e:
        print("[sahayak] gemini failed:", e)
        return fallback


def phrases_for_scenario(scenario: str):
    return [p for p in PHRASES.values() if p["scenario"] == scenario]
