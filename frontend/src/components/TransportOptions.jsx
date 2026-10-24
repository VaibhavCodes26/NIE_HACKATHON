
import { formatDuration } from '../services/routeService';
import {
  AlertTriangle,
  ArrowRight,
  Bus,
  Car,
  Check,
  ChevronDown,
  ChevronUp,
  Footprints,
  TrainFront,
  TramFront,
} from 'lucide-react';

export const MODES = [
  { id: 'taxi', title: 'Taxi', blurb: 'A comfortable, direct ride.', Icon: Car },
  { id: 'walking', title: 'Walking', blurb: 'Explore the route on foot.', Icon: Footprints },
  { id: 'train', title: 'Train', blurb: 'Connect between cities by rail.', Icon: TrainFront },
  { id: 'metro', title: 'Metro', blurb: 'Navigate urban routes with ease.', Icon: TramFront },
  { id: 'bus', title: 'Bus', blurb: 'Discover convenient bus connections.', Icon: Bus },
];

// Which mode-specific "extra" rows to show on the compact card (kept short for easy comparison)
const CARD_EXTRAS = { train: 2, metro: 1, bus: 1, taxi: 0, walking: 0 };

export default function TransportOptions({ routes, selected, onSelect, from, to }) {
  const availableModes = MODES.filter(({ id }) => {
    if (id === 'train') return true;
    const m = routes?.modes?.[id];
    return Boolean(m && m.available);
  });

  return (
    <section className="rd-transport" aria-labelledby="rd-transport-title">
      <div className="rd-container">
        <div className="rd-section-head">
          <p className="rd-eyebrow rd-eyebrow--dark">
            {from.name} <ArrowRight size={13} aria-hidden="true" /> {to.name}
          </p>
          <h2 id="rd-transport-title">How Will You Get There?</h2>
          <p>
            {availableModes.length > 0
              ? 'Compare your options and choose the journey that suits you.'
              : 'No verified direct transport routes were found for this destination pair.'}
          </p>
        </div>

        {availableModes.length > 0 ? (
          <ul className="rd-modes" role="radiogroup" aria-label="Transport options">
            {availableModes.map(({ id, title, blurb, Icon }) => {
              const m = routes?.modes?.[id] || { available: false };
              const isSel = selected === id;
              const extras = (m.extra || []).slice(0, CARD_EXTRAS[id] || 0);
              const formattedDist = m.available
                ? m.distanceKm < 10
                  ? `${Number(m.distanceKm).toFixed(1)} km`
                  : `${Math.round(m.distanceKm)} km`
                : '—';

              return (
                <li key={id}>
                  <article
                    className={`rd-mode rd-mode--${id} ${isSel ? 'is-selected' : ''} ${
                      m.available || id === 'train' ? '' : 'is-unavailable'
                    }`}
                  >
                    {isSel && (
                      <span className="rd-mode__check" aria-hidden="true">
                        <Check size={14} />
                      </span>
                    )}
                    <div className="rd-mode__icon" aria-hidden="true">
                      <Icon size={28} strokeWidth={1.8} />
                    </div>
                    <h3>{title}</h3>
                    <p className="rd-mode__blurb">{blurb}</p>

                    <dl className="rd-mode__stats">
                      <div>
                        <dt>Duration</dt>
                        <dd>{id === 'train' ? 'Search trains' : m.available ? formatDuration(m.durationMin) : '—'}</dd>
                      </div>
                      <div>
                        <dt>Distance</dt>
                        <dd>{id === 'train' ? 'Search trains' : formattedDist}</dd>
                      </div>
                      <div>
                        <dt>Est. fare</dt>
                        <dd>{id === 'train' ? 'Search trains' : m.available ? m.fare : '—'}</dd>
                      </div>
                      {m.available &&
                        extras.map((x) => (
                          <div key={x.label}>
                            <dt>{x.label}</dt>
                            <dd>{x.value}</dd>
                          </div>
                        ))}
                    </dl>

                    {id === 'walking' && m.warning && (
                      <p className="rd-mode__warn">
                        <AlertTriangle size={14} aria-hidden="true" />
                        {m.warning}
                      </p>
                    )}

                    {!m.available && id !== 'train' && <p className="rd-mode__na">Not available on this route</p>}

                    <button
                      type="button"
                      className="rd-mode__btn"
                      role="radio"
                      aria-checked={isSel}
                      aria-expanded={isSel}
                      onClick={() => onSelect(id)}
                    >
                      {isSel ? 'Hide Route' : 'View Route'}
                      {isSel ? (
                        <ChevronUp size={16} aria-hidden="true" />
                      ) : (
                        <ChevronDown size={16} aria-hidden="true" />
                      )}
                    </button>
                  </article>
                </li>
              );
            })}
          </ul>
        ) : null}

        <p className="rd-disclaimer">
          Route distances and durations are verified via Google Routes API and official operator schedules.
          Taxi fares are indicative estimates; train and bus fares are subject to operator availability.
        </p>
      </div>
    </section>
  );
}