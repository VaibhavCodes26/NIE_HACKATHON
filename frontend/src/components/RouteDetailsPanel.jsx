import { AlertTriangle, ArrowRight, Clock, IndianRupee, Info, Route as RouteIcon } from 'lucide-react';
import { formatDuration } from '../services/routeService';
import { MODES } from './TransportOptions';

export default function RouteDetailsPanel({ modeId, routes, from, to, onContinue }) {
  const meta = MODES.find((m) => m.id === modeId);
  const m = routes.modes[modeId];
  const { Icon } = meta;

  return (
    <section
      className="rd-details"
      aria-labelledby="rd-details-title"
      aria-live="polite"
      key={modeId} // re-trigger entrance animation per mode
    >
      <div className="rd-container">
        <div className="rd-details__card">
          <header className="rd-details__head">
            <span className="rd-details__icon" aria-hidden="true">
              <Icon size={30} strokeWidth={1.8} />
            </span>
            <div>
              <p className="rd-eyebrow rd-eyebrow--dark">Route details · {meta.title}</p>
              <h2 id="rd-details-title">
                {from.name} <ArrowRight size={22} aria-hidden="true" /> {to.name}
              </h2>
            </div>
          </header>

          {m.warning && (
            <div className="rd-alert rd-alert--warn" role="alert">
              <AlertTriangle size={18} aria-hidden="true" />
              <p>{m.warning}</p>
            </div>
          )}

          {!m.available ? (
            <div className="rd-alert rd-alert--info">
              <Info size={18} aria-hidden="true" />
              <p>{meta.title} is not available for this journey. {m.steps[0]}</p>
            </div>
          ) : (
            <>
              <div className="rd-details__grid">
                <div className="rd-details__summary">
                  <h3>Route summary</h3>
                  <p>{m.summary}</p>

                  <ol className="rd-steps">
                    {m.steps.map((s, i) => (
                      <li key={s}>
                        <span className="rd-steps__dot">{i + 1}</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                <div className="rd-details__stats">
                  <div className="rd-stat">
                    <RouteIcon size={20} aria-hidden="true" />
                    <span>Estimated distance</span>
                    <strong>{Math.round(m.distanceKm)} km</strong>
                  </div>
                  <div className="rd-stat">
                    <Clock size={20} aria-hidden="true" />
                    <span>Estimated duration</span>
                    <strong>{formatDuration(m.durationMin)}</strong>
                  </div>
                  <div className="rd-stat">
                    <IndianRupee size={20} aria-hidden="true" />
                    <span>Estimated fare</span>
                    <strong>{m.fare}</strong>
                    {m.fareNote && <small>{m.fareNote}</small>}
                  </div>
                  {m.extra?.map((x) => (
                    <div className="rd-stat rd-stat--plain" key={x.label}>
                      <span>{x.label}</span>
                      <strong>{x.value}</strong>
                    </div>
                  ))}
                </div>
              </div>

              {m.notes?.length > 0 && (
                <ul className="rd-notes">
                  {m.notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              )}
            </>
          )}

          <footer className="rd-details__foot">
            <p>
              <Info size={14} aria-hidden="true" /> Illustrative prototype information — not live data.
            </p>
            {onContinue && m.available && (
              <button type="button" className="rd-cta rd-cta--sm" onClick={() => onContinue({ from, to, mode: modeId, route: m })}>
                Continue Planning <ArrowRight size={16} aria-hidden="true" />
              </button>
            )}
          </footer>
        </div>
      </div>
    </section>
  );
}