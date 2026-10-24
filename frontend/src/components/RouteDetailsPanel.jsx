
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  ExternalLink,
  IndianRupee,
  Info,
  Route as RouteIcon,
} from 'lucide-react';

import { formatDuration } from '../services/routeService';
import { MODES } from './TransportOptions';
import RouteMap from './RouteMap';

/**
 * Build a safe Uber mobile deep-link from origin/destination coordinates.
 * https://developer.uber.com/docs/riders/ride-requests/tutorials/deep-links/introduction
 */
function buildUberUrl(from, to) {
  const params = new URLSearchParams({
    action: 'setPickup',
    'pickup[latitude]': String(from.lat),
    'pickup[longitude]': String(from.lng),
    'pickup[nickname]': from.name,
    'dropoff[latitude]': String(to.lat),
    'dropoff[longitude]': String(to.lng),
    'dropoff[nickname]': to.name,
  });
  return `https://m.uber.com/ul/?${params.toString()}`;
}

/**
 * Build a RedBus route search URL for the given origin/destination city names.
 * RedBus canonical slug format: /bus-tickets/{from-city}-to-{to-city}
 * Names are lower-cased and spaces replaced with hyphens.
 */
function buildRedBusUrl(from, to) {
  const slug = (name) =>
    name.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  const fromSlug = slug(from.name);
  const toSlug = slug(to.name);
  return `https://www.redbus.in/bus-tickets/${fromSlug}-to-${toSlug}`;
}

export default function RouteDetailsPanel({
  modeId,
  routes,
  from,
  to,
  onContinue,
}) {
  const meta = MODES.find((mode) => mode.id === modeId);
  const m = routes?.modes?.[modeId];

  if (!meta || !m) return null;

  const { Icon } = meta;

  // Walking directions can be lengthy; show only a few useful steps.
  const visibleSteps = (m.steps || []).slice(
    0,
    modeId === 'walking' ? 3 : 5
  );

  const isWalking = modeId === 'walking';
  const isTrain = modeId === 'train';

  return (
    <section
      className="rd-details"
      aria-labelledby="rd-details-title"
      aria-live="polite"
      key={modeId}
    >
      <div className="rd-container">
        <div className="rd-details__card">
          <header className="rd-details__head">
            <span className="rd-details__icon" aria-hidden="true">
              <Icon size={30} strokeWidth={1.8} />
            </span>

            <div>
              <p className="rd-eyebrow rd-eyebrow--dark">
                Route details · {meta.title}
              </p>

              <h2 id="rd-details-title">
                {from.name} <ArrowRight size={22} aria-hidden="true" />{' '}
                {to.name}
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
              <p>
                {meta.title} route details are not available here.
                {m.steps?.[0] ? ` ${m.steps[0]}` : ''}
                {isTrain
                  ? ' Use the existing Find Your Train facility to search for trains.'
                  : ''}
              </p>
            </div>
          ) : (
            <>
              <div className="rd-details__grid">
                <div className="rd-details__summary">
                  <h3>
                    {isWalking ? 'Walking directions' : 'Route summary'}
                  </h3>

                  <p>
                    {isWalking
                      ? `Walk from ${from.name} to ${to.name}.`
                      : m.summary}
                  </p>

                  {visibleSteps.length > 0 && (
                    <ol className="rd-steps">
                      {visibleSteps.map((step, index) => (
                        <li key={`${index}-${step}`}>
                          <span className="rd-steps__dot">
                            {index + 1}
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  )}

                  {m.steps?.length > visibleSteps.length && (
                    <p className="rd-details__more">
                      Showing {visibleSteps.length} of {m.steps.length}{' '}
                      directions.
                    </p>
                  )}
                </div>

                <div className="rd-details__stats">
                  <div className="rd-stat">
                    <RouteIcon size={20} aria-hidden="true" />
                    <span>Estimated distance</span>
                    <strong>
                      {Number.isFinite(Number(m.distanceKm))
                        ? `${Number(m.distanceKm).toFixed(1)} km`
                        : 'Unavailable'}
                    </strong>
                  </div>

                  <div className="rd-stat">
                    <Clock size={20} aria-hidden="true" />
                    <span>Estimated duration</span>
                    <strong>
                      {Number.isFinite(Number(m.durationMin)) &&
                        Number(m.durationMin) > 0
                        ? formatDuration(m.durationMin)
                        : 'Unavailable'}
                    </strong>
                  </div>

                  {!isWalking && (
                    <div className="rd-stat">
                      <IndianRupee size={20} aria-hidden="true" />
                      <span>Estimated fare</span>
                      <strong>{m.fare || 'Not verified'}</strong>
                      {m.fareNote && <small>{m.fareNote}</small>}
                    </div>
                  )}
                </div>
              </div>

              <RouteMap
                from={from}
                to={to}
                modeId={modeId}
                polyline={m.polyline}
              />

              {m.notes?.length > 0 && (
                <ul className="rd-notes">
                  {(isWalking ? m.notes.slice(0, 1) : m.notes.slice(0, 2))
                    .map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                </ul>
              )}
            </>
          )}

          <footer className="rd-details__foot">
            <p>
              <Info size={14} aria-hidden="true" />
              Estimates depend on the routing provider. Fares and schedules
              may not be verified.
            </p>

            <div className="rd-details__actions">
              {/* Uber deep-link for Taxi */}
              {modeId === 'taxi' && m.available && (
                <a
                  href={buildUberUrl(from, to)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rd-cta rd-cta--sm rd-book-link"
                  id="rd-book-uber"
                  aria-label={`Book taxi from ${from.name} to ${to.name} via Uber`}
                >
                  Book Taxi
                  <ExternalLink size={15} aria-hidden="true" />
                </a>
              )}

              {/* RedBus search link for Bus */}
              {modeId === 'bus' && m.available && (
                <a
                  href={buildRedBusUrl(from, to)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rd-cta rd-cta--sm rd-book-link"
                  id="rd-book-redbus"
                  aria-label={`Find bus tickets from ${from.name} to ${to.name} via RedBus`}
                >
                  Find Bus Tickets
                  <ExternalLink size={15} aria-hidden="true" />
                </a>
              )}

              {onContinue && m.available && (
                <button
                  type="button"
                  className="rd-cta rd-cta--sm"
                  onClick={() =>
                    onContinue({
                      from,
                      to,
                      mode: modeId,
                      route: m,
                    })
                  }
                >
                  Continue Planning
                  <ArrowRight size={16} aria-hidden="true" />
                </button>
              )}
            </div>
          </footer>

        </div>
      </div>
    </section>
  );
}
