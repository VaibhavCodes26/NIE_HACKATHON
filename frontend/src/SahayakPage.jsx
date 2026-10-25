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
  const [listening, setListening] = useState(false);
  const [toast, setToast] = useState("");
  const recRef = useRef(null);

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
  function speak(text) {
    if (!("speechSynthesis" in window)) return flash("Speech is not supported on this browser.");
    const u = new SpeechSynthesisUtterance(text.replace("…", ""));
    u.lang = "kn-IN";
    u.rate = 0.85;
    const v = window.speechSynthesis.getVoices().find((x) => x.lang.toLowerCase().startsWith("kn"));
    if (!v) flash("No Kannada voice on this device. Use 'Show' instead.");
    else u.voice = v;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
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
                <button onClick={() => speak(p.kn)}>🔊 Play</button>
                <button onClick={() => setShowPhrase(p)}>Show</button>
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
            onClick={(e) => {
              e.stopPropagation();
              speak(showPhrase.kn);
            }}
          >
            🔊 Play
          </button>
          <small>Tap anywhere to close</small>
        </div>
      )}

      {toast && <div className="sh-toast">{toast}</div>}
    </main>
  );
}
