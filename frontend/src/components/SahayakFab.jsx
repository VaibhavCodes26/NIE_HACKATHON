import { useEffect, useState } from "react";
import SahayakPage from "../SahayakPage.jsx";
import "./sahayak-fab.css";

const HINT_KEY = "sahayak_hint_seen";

// localStorage can be blocked (private mode etc.), so every access is guarded.
// Demo tip: add ?hint to any page URL (e.g. localhost:5173/?hint) to see the tooltip + pulse again.
function hintSeen() {
  try {
    if (new URLSearchParams(window.location.search).has("hint")) return false;
    return localStorage.getItem(HINT_KEY) === "1";
  } catch {
    return false;
  }
}

function markHintSeen() {
  try {
    localStorage.setItem(HINT_KEY, "1");
  } catch {
    /* ignore */
  }
}

/**
 * Floating Namma Sahayak button.
 * Works without react-router-dom. Mount once, outside <Routes>.
 */
export default function SahayakFab({ journeyConfig }) {
  const [open, setOpen] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [pulse, setPulse] = useState(() => !hintSeen());

  // First-visit hint: appears after 2s, hides itself after 10s.
  useEffect(() => {
    if (hintSeen()) return;
    const show = setTimeout(() => setShowHint(true), 2000);
    const hide = setTimeout(() => setShowHint(false), 10000);
    return () => {
      clearTimeout(show);
      clearTimeout(hide);
    };
  }, []);

  // Close chatbot when Escape is pressed.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function toggle() {
    setOpen((previous) => !previous);
    setShowHint(false);
    setPulse(false);
    markHintSeen();
  }

  function dismissHint() {
    setShowHint(false);
    setPulse(false);
    markHintSeen();
  }

  return (
    <>
      {showHint && !open && (
        <div className="sfab-hint" role="status">
          <button
            className="sfab-hint-x"
            onClick={dismissHint}
            aria-label="Dismiss tip"
          >
            ×
          </button>
          <strong>Speak Kannada in one tap</strong>
          <span>
            Phrases for autos, food, temples and more. Show them or play them
            aloud.
          </span>
        </div>
      )}

      <button
        className={`sfab ${open ? "is-open" : ""} ${pulse && !open ? "pulse" : ""}`}
        onClick={toggle}
        aria-label={open ? "Close Namma Sahayak" : "Open Namma Sahayak"}
        aria-expanded={open}
      >
        {open ? (
          <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
            <path
              d="M6 6l12 12M18 6L6 18"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        ) : (
          <span className="sfab-kn" aria-hidden="true">
            ಸ
          </span>
        )}
      </button>

      {/* Always mounted (just hidden) so the conversation survives open/close and page changes */}
      <div
        className={`sfab-panel ${open ? "open" : ""}`}
        role="dialog"
        aria-label="Namma Sahayak"
        aria-hidden={!open}
      >
        <button
          className="sfab-close"
          onClick={() => setOpen(false)}
          aria-label="Close"
        >
          ×
        </button>

        <SahayakPage journeyConfig={journeyConfig} compact />
      </div>
    </>
  );
}
