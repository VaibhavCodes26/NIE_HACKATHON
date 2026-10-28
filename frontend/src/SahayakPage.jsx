import { useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";
import "./sahayak.css";

const API = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const LANGS = [
  { id: "en", label: "English", speech: "en-IN", placeholder: "e.g. How do I bargain with an auto driver?" },
  { id: "hi", label: "हिन्दी", speech: "hi-IN", placeholder: "जैसे: ऑटो वाले से भाव कैसे करूँ?" },
  { id: "mr", label: "मराठी", speech: "mr-IN", placeholder: "उदा. रिक्षावाल्याशी भाव कसा करू?" },
];

// Pass your journeyConfig and onBack callback as props.
export default function SahayakPage({ journeyConfig, onBack, compact = false }) {
  const [lang, setLang] = useState("en");
  const [query, setQuery] = useState("");
  const [scenarios, setScenarios] = useState([]);
  const [activeScenario, setActiveScenario] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPhrase, setShowPhrase] = useState(null); // full-screen "show to local"
  const [toast, setToast] = useState("");
  const [audioState, setAudioState] = useState({ text: "", loading: false, playing: false });
  const recRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
        audioRef.current = null;
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const dest = journeyConfig?.destinations?.[0];
  const context = {
    city: typeof dest === "string" ? dest : dest?.name,
    travellers: journeyConfig?.travellers,
    budget: journeyConfig?.budget,
    style: journeyConfig?.travelStyle,
  };

  useEffect(() => {
    fetch(`${API}/api/sahayak/scenarios`)
      .then((r) => r.json())
      .then(setScenarios)
      .catch(() => setError("Could not reach the server. Is the backend running?"));
  }, []);

  const flash = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2800);
  };

  // ---- scenario cards: instant, no AI call ----
  async function openScenario(s) {
    setActiveScenario(s.id);
    setError("");
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sahayak/phrases?scenario=${s.id}`);
      const list = await r.json();
      setResult({ answer: "", tips: [], phrases: list.map((p) => ({ ...p, meaning: p.en })) });
    } catch {
      setError("Could not load phrases.");
    } finally {
      setLoading(false);
    }
  }

  // ---- free-text question: RAG + Gemini ----
  async function ask(text = query) {
    if (text.trim().length < 2) return;
    setError("");
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sahayak/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, language: lang, scenario: activeScenario, context }),
      });
      if (!r.ok) throw new Error();
      setResult(await r.json());
    } catch {
      setError("Something went wrong. Try again, or tap a scenario card above.");
    } finally {
      setLoading(false);
    }
  }

  // ---- voice input (Chrome / Android) ----
  function toggleMic() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return flash("Voice input needs Chrome or Edge.");
    if (listening) return recRef.current?.stop();
    const rec = new SR();
    rec.lang = LANGS.find((l) => l.id === lang).speech;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      setQuery(text);
      ask(text);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => {
      setListening(false);
      flash("Could not hear you. Try again.");
    };
    recRef.current = rec;
    setListening(true);
    rec.start();
  }

  // ---- Kannada speech output ----
  // Chromium browsers load voices asynchronously. getVoices() returns [] until
  // the 'voiceschanged' event fires, causing audio to silently fail in production.
  function getVoicesAsync() {
    return new Promise((resolve) => {
      if (!("speechSynthesis" in window)) {
        resolve([]);
        return;
      }
      const voices = window.speechSynthesis.getVoices();
      if (voices.length > 0) { resolve(voices); return; }
      const onChanged = () => {
        window.speechSynthesis.removeEventListener("voiceschanged", onChanged);
        resolve(window.speechSynthesis.getVoices());
      };
      window.speechSynthesis.addEventListener("voiceschanged", onChanged);
      // Safety: resolve with whatever is available after 1.5s to avoid hanging
      setTimeout(() => {
        window.speechSynthesis.removeEventListener("voiceschanged", onChanged);
        resolve(window.speechSynthesis.getVoices());
      }, 1500);
    });
  }

  async function speak(text) {
    const clean = (text || "").replace(/[….]/g, " ").trim();
    if (!clean) return;

    // If currently playing this exact phrase, toggle stop
    if (audioRef.current && audioState.text === clean && audioState.playing) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setAudioState({ text: "", loading: false, playing: false });
      return;
    }

    // Stop previous audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }

    setAudioState({ text: clean, loading: true, playing: false });

    // Fallback: only use local speech synthesis if a genuine Kannada voice is installed
    const tryLocalVoiceFallback = async () => {
      const voices = await getVoicesAsync();
      const knVoice = voices.find((x) => x.lang?.toLowerCase().startsWith("kn"));
      if (knVoice) {
        const u = new SpeechSynthesisUtterance(clean);
        u.voice = knVoice;
        u.lang = "kn-IN";
        u.rate = 0.85;
        u.onend = () => setAudioState({ text: "", loading: false, playing: false });
        u.onerror = () => setAudioState({ text: "", loading: false, playing: false });
        window.speechSynthesis.speak(u);
        setAudioState({ text: clean, loading: false, playing: true });
        return true;
      }
      // Never use an incorrect non-Kannada voice; show polite fallback
      setAudioState({ text: "", loading: false, playing: false });
      flash("Kannada audio is temporarily unavailable. Use 'Show' to display the phrase to locals.");
      return false;
    };

    // Primary: Backend Kannada TTS (works reliably on any device without local Kannada voice)
    try {
      const audioUrl = `${API}/api/sahayak/tts?text=${encodeURIComponent(clean)}`;
      const audio = new Audio();
      audioRef.current = audio;
      audio.preload = "auto";
      audio.src = audioUrl;

      audio.onplay = () => {
        setAudioState({ text: clean, loading: false, playing: true });
      };

      audio.onended = () => {
        setAudioState({ text: "", loading: false, playing: false });
      };

      audio.onerror = async () => {
        await tryLocalVoiceFallback();
      };

      await audio.play();
    } catch (playErr) {
      if (playErr.name !== "AbortError") {
        await tryLocalVoiceFallback();
      }
    }
  }

  const translit = (p) => (lang === "en" ? p.roman : p.deva);
  const phrases = result?.phrases || [];
  const suggested = phrases.find((p) => p.id === result?.show_to_local_id);

  return (
    <main className={`sh ${compact ? "sh--compact" : ""}`}>
      {onBack && (
        <div className="sh-topbar">
          <button className="sh-back-btn" onClick={onBack} aria-label="Back to NammaPrayana">
            <ArrowLeft size={18} aria-hidden="true" />
            <span>Back to NammaPrayana</span>
          </button>
        </div>
      )}
      <header className="sh-head">
        <h1>
          ನಮ್ಮ ಸಹಾಯಕ <span>Namma Sahayak</span>
        </h1>
        <p>Ask in {LANGS.find((l) => l.id === lang).label}. Get the exact Kannada to say, show or play.</p>
        <div className="sh-langs" role="group" aria-label="Your language">
          {LANGS.map((l) => (
            <button key={l.id} className={lang === l.id ? "on" : ""} onClick={() => setLang(l.id)}>
              {l.label}
            </button>
          ))}
        </div>
      </header>

      <div className="sh-ask">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder={LANGS.find((l) => l.id === lang).placeholder}
          aria-label="Ask Namma Sahayak"
        />
        <button className={`mic ${listening ? "live" : ""}`} onClick={toggleMic} aria-label="Speak your question">
          {listening ? "Listening…" : "🎤"}
        </button>
        <button className="go" onClick={() => ask()} disabled={loading}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </div>

      <div className="sh-scn">
        {scenarios.map((s) => (
          <button key={s.id} className={activeScenario === s.id ? "on" : ""} onClick={() => openScenario(s)}>
            <span>{s.icon}</span> {s.label}
          </button>
        ))}
      </div>

      {error && <p className="sh-err">{error}</p>}

      {result && (
        <section className="sh-res">
          {result.answer && <p className="sh-answer">{result.answer}</p>}

          {suggested && (
            <button className="sh-hero" onClick={() => setShowPhrase(suggested)}>
              <span className="kn">{suggested.kn}</span>
              <span className="hint">Tap to show this to the person you're talking to </span>
            </button>
          )}

          {phrases.map((p) => (
            <article key={p.id} className="sh-card">
              <div className="kn">{p.kn}</div>
              <div className="rm">{translit(p)}</div>
              {lang !== "en" && <div className="rm2">{p.roman}</div>}
              <div className="mn">{p.meaning}</div>
              <div className="act">
                <button
                  type="button"
                  onClick={() => speak(p.kn)}
                  disabled={audioState.loading && audioState.text === (p.kn || "").replace(/[….]/g, " ").trim()}
                  className={audioState.playing && audioState.text === (p.kn || "").replace(/[….]/g, " ").trim() ? "is-playing" : ""}
                  aria-label={`Play audio for ${p.kn}`}
                >
                  {audioState.loading && audioState.text === (p.kn || "").replace(/[….]/g, " ").trim()
                    ? "⏳ Loading…"
                    : audioState.playing && audioState.text === (p.kn || "").replace(/[….]/g, " ").trim()
                    ? "⏹ Stop"
                    : "🔊 Play"}
                </button>
                <button type="button" onClick={() => setShowPhrase(p)}>Show</button>
              </div>
            </article>
          ))}

          {result.tips?.length > 0 && (
            <div className="sh-tips">
              <h3>Local tips</h3>
              <ul>
                {result.tips.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="sh-foot">Phrases come from a curated phrasebook. Ask a local to confirm anything important.</p>

          {result.sources?.length > 0 && (
            <p className="sh-src">
              <strong>Sources:</strong> {result.sources.map((x) => x.label).join(" · ")}
              {result.retrieval && (
                <em> · {result.retrieval === "embeddings" ? "semantic search" : "keyword search"}</em>
              )}
            </p>
          )}
        </section>
      )}

      {showPhrase && (
        <div className="sh-full" onClick={() => setShowPhrase(null)} role="dialog" aria-modal="true">
          <div className="kn">{showPhrase.kn}</div>
          <div className="rm">{showPhrase.roman}</div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              speak(showPhrase.kn);
            }}
            disabled={audioState.loading && audioState.text === (showPhrase.kn || "").replace(/[….]/g, " ").trim()}
            className={audioState.playing && audioState.text === (showPhrase.kn || "").replace(/[….]/g, " ").trim() ? "is-playing" : ""}
          >
            {audioState.loading && audioState.text === (showPhrase.kn || "").replace(/[….]/g, " ").trim()
              ? "⏳ Loading…"
              : audioState.playing && audioState.text === (showPhrase.kn || "").replace(/[….]/g, " ").trim()
              ? "⏹ Stop"
              : "🔊 Play"}
          </button>
          <small>Tap anywhere to close</small>
        </div>
      )}

      {toast && <div className="sh-toast">{toast}</div>}
    </main>
  );
}
