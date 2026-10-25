import { useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  Flame,
  Footprints,
  Info,
  MapPin,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import "./gati-meter.css";

const API = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

/**
 * Live pacing preview call to Namma Gati backend endpoint.
 */
export async function fetchGatiPlan({
  stops,
  days,
  cities,
  profile,
  pace = "balanced",
  startDate = null,
}) {
  const r = await fetch(`${API}/api/gati/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stops,
      days,
      cities,
      profile,
      pace,
      start_date: startDate,
    }),
  });
  if (!r.ok) throw new Error("Could not compute the stamina effort plan");
  return r.json();
}

const STATUS_CONFIG = {
  ok: { label: "Comfortable", class: "ok", desc: "Well-balanced daily pace" },
  heavy: { label: "Heavy Day", class: "heavy", desc: "High effort · take frequent breaks" },
  light: { label: "Light Day", class: "light", desc: "Easy pace · plenty of leisure" },
  free: { label: "Flexible Day", class: "free", desc: "Free day for rest or spontaneous discovery" },
};

export default function GatiMeter({ gati, compact = false, onSelectDay = null, activeDayIndex = null }) {
  if (!gati?.days?.length) return null;

  const summary = gati.summary || {};
  const capacity = summary.capacity || 110;
  const pace = summary.pace || "balanced";
  const pacedFor = summary.paced_for || [];
  const maxStops = summary.max_stops || 5;

  const hasHeavyDays = gati.days.some((d) => d.status === "heavy");
  const hasFreeDays = gati.days.some((d) => d.status === "free");
  const totalEffort = summary.total_effort || gati.days.reduce((acc, d) => acc + (d.total || 0), 0);

  const planAssessment = useMemo(() => {
    if (gati.warnings?.some((w) => w.toLowerCase().includes("only have") || w.toLowerCase().includes("not enough days"))) {
      return { text: "Time Constrained", tag: "constrained", desc: "More days recommended for this route" };
    }
    if (hasHeavyDays) {
      return { text: "Demanding Route", tag: "heavy", desc: "Includes high-effort destinations; rest built in" };
    }
    if (pace === "relaxed") {
      return { text: "Leisurely & Relaxed", tag: "ok", desc: "Gentle stamina demand with generous buffers" };
    }
    return { text: "Comfortable & Balanced", tag: "ok", desc: "Optimised for healthy group stamina" };
  }, [hasHeavyDays, pace, gati.warnings]);

  return (
    <section className={`gm ${compact ? "gm--compact" : ""}`} aria-label="Namma Gati Stamina & Effort Plan">
      {/* Header with Karnataka Red/Turmeric Badges */}
      <header className="gm-head">
        <div className="gm-head__main">
          <div className="gm-badge-row">
            <span className="gm-pill gm-pill--brand">
              <Activity size={13} /> Namma Gati
            </span>
            <span className={`gm-pill gm-pill--${planAssessment.tag}`}>
              {planAssessment.text}
            </span>
            <span className="gm-pill gm-pill--pace">
              Pace: {pace.charAt(0).toUpperCase() + pace.slice(1)}
            </span>
          </div>
          <h3>Stamina-Aware Effort & Pacing</h3>
          <p>
            {pacedFor.length
              ? `Adjusted for ${pacedFor.join(", ")}.`
              : "Calibrated for a healthy adult travelling group."}{" "}
            Daily stamina budget: <strong>{capacity} effort points</strong> (max ~{maxStops} stops/day).
          </p>
        </div>

        <div className="gm-head__stats">
          <div className="gm-stat-item">
            <span className="gm-stat-label">Daily Budget</span>
            <strong className="gm-stat-val">{capacity} pts</strong>
          </div>
          <div className="gm-stat-item">
            <span className="gm-stat-label">Trip Effort</span>
            <strong className="gm-stat-val">{totalEffort} pts</strong>
          </div>
          <div className="gm-stat-item">
            <span className="gm-stat-label">Days Planned</span>
            <strong className="gm-stat-val">{gati.days.length}</strong>
          </div>
        </div>
      </header>

      {/* Warnings & Advisories */}
      {Array.isArray(gati.warnings) && gati.warnings.length > 0 && (
        <div className="gm-warnings">
          {gati.warnings.map((w, i) => (
            <div className="gm-warn" key={i}>
              <AlertTriangle size={15} />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Day by Day Effort Meter Cards */}
      <div className="gm-days-grid">
        {gati.days.map((d, idx) => {
          const cfg = STATUS_CONFIG[d.status] || STATUS_CONFIG.ok;
          const dayCap = d.capacity || capacity;
          const pct = Math.min(100, Math.round(((d.total || 0) / dayCap) * 100));
          const isSelected = activeDayIndex === idx;

          return (
            <article
              className={`gm-day ${d.status} ${isSelected ? "is-active" : ""}`}
              key={d.day_number || d.day || idx}
              onClick={() => onSelectDay && onSelectDay(idx)}
              style={onSelectDay ? { cursor: "pointer" } : undefined}
            >
              <div className="gm-row">
                <div className="gm-day-title">
                  <strong>Day {d.day_number || d.day}</strong>
                  {d.destination && <span className="gm-day-dest">· {d.destination}</span>}
                  {d.date && <small className="gm-day-date">({d.date})</small>}
                </div>
                <span className={`gm-tag ${cfg.class}`}>{cfg.label}</span>
              </div>

              <div
                className="gm-bar"
                role="meter"
                aria-label={`Day ${d.day_number || d.day} effort`}
                aria-valuemin={0}
                aria-valuemax={dayCap}
                aria-valuenow={Math.min(d.total || 0, dayCap)}
              >
                <span
                  className={cfg.class}
                  style={{ width: `${Math.max(5, pct)}%` }}
                />
              </div>

              <div className="gm-bar-meta">
                <span className="gm-bar-desc">{cfg.desc}</span>
                <span className="gm-num">
                  <strong>{d.total || 0}</strong> / {dayCap} pts ({pct}%)
                </span>
              </div>

              {/* Scheduled Stops with Effort Badges */}
              {Array.isArray(d.stops) && d.stops.length > 0 ? (
                <ul className="gm-stops">
                  {d.stops.map((s, sIdx) => {
                    const level = s.level || (s.effort < 25 ? "low" : s.effort < 50 ? "medium" : "high");
                    return (
                      <li key={s.id ?? `${idx}-${sIdx}`}>
                        <span className={`dot ${level}`} title={`Effort level: ${level}`} />
                        <span className="gm-stop-name">{s.name}</span>
                        {s.category && <small className="gm-stop-cat">{s.category}</small>}
                        <span className={`gm-effort-badge ${level}`}>
                          {s.effort != null ? `${s.effort} pts` : level}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="gm-empty-note">
                  <Compass size={13} /> Free day to explore local lanes or rest.
                </p>
              )}

              {/* Guidance & Break Notes */}
              {Array.isArray(d.notes) && d.notes.length > 0 && (
                <div className="gm-notes-list">
                  {d.notes.map((n, i) => (
                    <p className="gm-note" key={i}>
                      <Info size={12} /> {n}
                    </p>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>

      {/* Deferred Attractions Section */}
      {Array.isArray(gati.deferred) && gati.deferred.length > 0 && (
        <aside className="gm-deferred-section" aria-label="Deferred attractions">
          <div className="gm-deferred-header">
            <ShieldAlert size={18} className="gm-deferred-icon" />
            <div>
              <strong>Set Aside for Comfort ({gati.deferred.length})</strong>
              <p>
                To keep your daily travel within safe, comfortable stamina thresholds,
                these attractions were not scheduled into the main itinerary.
              </p>
            </div>
          </div>

          <div className="gm-deferred-cards">
            {gati.deferred.map((x, i) => (
              <div className="gm-deferred-item" key={x.id ?? i}>
                <div className="gm-deferred-top">
                  <span className="gm-deferred-name">{x.name}</span>
                  {x.effort != null && (
                    <span className="gm-deferred-effort">Effort {x.effort}</span>
                  )}
                </div>
                {x.city && <span className="gm-deferred-city"><MapPin size={11} /> {x.city}</span>}
                <p className="gm-deferred-reason">
                  {x.reason || (x.code === "strenuous" ? "Too strenuous for group profile" : "Exceeds daily schedule capacity")}
                </p>
              </div>
            ))}
          </div>
        </aside>
      )}
    </section>
  );
}
