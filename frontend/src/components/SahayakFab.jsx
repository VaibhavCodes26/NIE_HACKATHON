
import { useEffect, useState } from "react";
import SahayakPage from "../SahayakPage.jsx";
import "./sahayak-fab.css";

/**
 * Floating Namma Sahayak button.
 * Tooltip and pulse restart on every page reload.
 * No react-router-dom required.
 */
export default function SahayakFab({ journeyConfig }) {
  const [open, setOpen] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [pulse, setPulse] = useState(true);

  // Show tooltip 2 seconds after every page load.
  // Hide it 10 seconds after it appears.
  useEffect(() => {
    const showTimer = setTimeout(() => {
      setShowHint(true);
    }, 2000);

    const hideTimer = setTimeout(() => {
      setShowHint(false);
    }, 12000);

    return () => {
      clearTimeout(showTimer);
      clearTimeout(hideTimer);
    };
  }, []);

  // Respect the user's reduced-motion preference.
  useEffect(() => {
    const mediaQuery = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    if (mediaQuery.matches) {
      setPulse(false);
    }

    const handleMotionChange = (event) => {
      setPulse(!event.matches);
    };

    mediaQuery.addEventListener("change", handleMotionChange);

    return () => {
      mediaQuery.removeEventListener("change", handleMotionChange);
    };
  }, []);

  // Close the popup when Escape is pressed.
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  function toggle() {
    setOpen((previous) => !previous);
    setShowHint(false);
    setPulse(false);
  }

  function dismissHint() {
    setShowHint(false);
    setPulse(false);
  }

  return (
    <>
      {/* Tooltip: visible only when the popup is closed */}
      {showHint && !open && (
        <div className="sfab-hint" role="status">
          <button
            type="button"
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

      {/* Floating action button */}
      <button
        type="button"
        className={`sfab ${open ? "is-open" : ""} ${
          pulse && !open ? "pulse" : ""
        }`}
        onClick={toggle}
        aria-label={open ? "Close Namma Sahayak" : "Open Namma Sahayak"}
        aria-expanded={open}
      >
        {open ? (
          <svg
            viewBox="0 0 24 24"
            width="26"
            height="26"
            aria-hidden="true"
          >
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

      {/* Keep the panel mounted to preserve the conversation */}
      <div
        className={`sfab-panel ${open ? "open" : ""}`}
        role="dialog"
        aria-label="Namma Sahayak"
        aria-hidden={!open}
      >
        <button
          type="button"
          className="sfab-close"
          onClick={() => setOpen(false)}
          aria-label="Close"
          tabIndex={open ? 0 : -1}
        >
          ×
        </button>

        <SahayakPage journeyConfig={journeyConfig} compact />
      </div>
    </>
  );
}