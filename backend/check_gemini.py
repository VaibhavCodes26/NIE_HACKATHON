import json, os, sys
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

key = os.getenv("GEMINI_API_KEY")
print("1) GEMINI_API_KEY loaded:", "YES" if key else "NO  <-- put it in backend/.env (GEMINI_API_KEY=...)")
if not key:
    sys.exit(1)

client = genai.Client(api_key=key)
gen = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
emb = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

try:
    names = [m.name.replace("models/", "") for m in client.models.list()]
    print("2) Key works. Available models (sample):", [n for n in names if "flash" in n or "embedding" in n][:12])
except Exception as e:
    print("2) Could not list models:", repr(e))

try:
    r = client.models.generate_content(
        model=gen, contents='Reply with JSON {"ok": true}',
        config=types.GenerateContentConfig(response_mime_type="application/json"))
    print(f"3) Generation OK with '{gen}':", json.loads(r.text))
except Exception as e:
    print(f"3) Generation FAILED with '{gen}':", repr(e))

try:
    r = client.models.embed_content(model=emb, contents=["test"])
    print(f"4) Embeddings OK with '{emb}' (dimension {len(r.embeddings[0].values)})")
except Exception as e:
    print(f"4) Embeddings FAILED with '{emb}':", repr(e))
