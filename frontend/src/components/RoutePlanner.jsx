import { ArrowLeftRight, ArrowRight, Loader2 } from 'lucide-react';
import LocationField from './LocationField';
import { LatticeBackdrop } from './Motifs';
import { DESTINATIONS, START_LOCATIONS } from '../data/locations';

export default function RoutePlanner({
  from,
  to,
  errors,
  loading,
  onFromChange,
  onToChange,
  onSwap,
  onSubmit,
}) {
  return (
    <section className="rd-planner" aria-labelledby="rd-plan-title">
      <div className="rd-container">
        <div className="rd-planner__head">
          <h2 id="rd-plan-title">Plan Your Route</h2>
          <p>Choose your starting point and destination to discover the best ways to explore Karnataka.</p>
        </div>

        <form
          className="rd-planner__card"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
          noValidate
        >
          <LatticeBackdrop className="rd-planner__lattice" />

          <div className="rd-planner__fields">
            <LocationField
              variant="start"
              label="Starting From"
              placeholder="Enter starting city, landmark or station"
              options={START_LOCATIONS}
              value={from}
              onChange={onFromChange}
              error={errors.from}
            />

            <button
              type="button"
              className="rd-swap"
              onClick={onSwap}
              aria-label="Swap starting point and destination"
              title="Swap locations"
            >
              <ArrowLeftRight size={18} />
            </button>

            <LocationField
              variant="end"
              label="Travelling To"
              placeholder="Choose your destination"
              options={DESTINATIONS}
              value={to}
              onChange={onToChange}
              error={errors.to}
            />
          </div>

          {errors.same && (
            <p className="rd-planner__error" role="alert">
              {errors.same}
            </p>
          )}

          <button type="submit" className="rd-cta" disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={18} className="rd-spin" aria-hidden="true" /> Finding routes…
              </>
            ) : (
              <>
                Explore Routes <ArrowRight size={18} aria-hidden="true" />
              </>
            )}
          </button>
        </form>
      </div>
    </section>
  );
}