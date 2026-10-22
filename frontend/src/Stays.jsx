
import { useState } from 'react';
import {
  ArrowLeft,
  ExternalLink,
  Hotel,
  MapPin,
  Phone,
  RefreshCw,
  Sparkles,
  Star,
  Wallet,
  Compass,
} from 'lucide-react';
import './Stays.css';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

const DESTINATION_NAMES = {
  badami: 'Badami',
  hampi: 'Hampi',
  mysuru: 'Mysuru',
  bengaluru: 'Bengaluru',
  coorg: 'Coorg',
  chikkamagaluru: 'Chikkamagaluru',
  mangaluru: 'Mangaluru',
  udupi: 'Udupi',
  gokarna: 'Gokarna',
  dandeli: 'Dandeli',
  shivamogga: 'Shivamogga',
  'belur-halebidu': 'Belur and Halebidu',
  vijayapura: 'Vijayapura',
  bidar: 'Bidar',
  chitradurga: 'Chitradurga',
  belagavi: 'Belagavi',
  hubballi: 'Hubballi',
  hassan: 'Hassan',
};

const resolveDestination = (item) => {
  const id = typeof item === 'string' ? item : item?.id;
  return DESTINATION_NAMES[id] ||
    (typeof item === 'object' ? item?.name : id) ||
    '';
};

const formatINR = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);

function getPriceLabel(stay) {
  if (stay.estimated_price_inr == null) return 'Price not verified';

  const price = formatINR(stay.estimated_price_inr);

  if (stay.price_period === 'per_night') return `${price} / night`;
  if (stay.price_period === 'total_stay') return `${price} / total stay`;

  return `${price} · Period unclear`;
}

const NORMALIZE_TRAVEL_STYLE = {
  'budget-friendly': 'budget',
  budget: 'budget',
  'comfort-friendly': 'comfortable',
  comfortable: 'comfortable',
  comfort: 'comfortable',
  premium: 'premium',
  'ultra-premium': 'ultra-premium',
};

export default function Stays({ journeyConfig, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function findStays() {
    if (!journeyConfig) {
      setError('Journey preferences were not found. Please plan your trip again.');
      return;
    }

    setLoading(true);
    setError('');
    setData(null);

    const destinations = (journeyConfig.destinations || [])
      .map(resolveDestination)
      .filter(Boolean);

    try {
      const response = await fetch(`${API_BASE}/api/stays/recommendations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destinations,
          start_date: journeyConfig.startDate,
          end_date: journeyConfig.endDate,
          traveller_count: Number(journeyConfig.travellerCount),
          travel_style:
            NORMALIZE_TRAVEL_STYLE[journeyConfig.travelStyle] ||
            journeyConfig.travelStyle,
          total_budget: Number(journeyConfig.totalBudget),
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail || 'Could not find suitable stays right now.'
        );
      }

      setData(result);
    } catch (err) {
      setError(
        err.message ||
        'Could not connect to the backend. Check that the API server is running.'
      );
    } finally {
      setLoading(false);
    }
  }

  const destinations = (journeyConfig?.destinations || [])
    .map(resolveDestination)
    .filter(Boolean);

  return (
    <main className="stays-page">
      <div className="stays-flag-stripe" aria-hidden="true">
        <span />
        <span />
      </div>

      <header className="stays-topbar">
        <button className="stays-back" onClick={onBack}>
          <ArrowLeft size={18} />
          <span>Back to journey</span>
        </button>

        <a className="stays-brand" href="/" aria-label="NammaPrayana home">
          <span className="stays-brand-emblem"><Compass size={22} /></span>
          <span className="stays-brand-words">
            NAMMA<span>PRAYANA</span>
            <small>EXPLORE KARNATAKA</small>
          </span>
        </a>

        <div className="stays-top-label">
          <span /> AI STAY FINDER
        </div>
      </header>

      <section className="stays-hero">
        <div className="stays-hero-pattern" aria-hidden="true" />

        <div className="stays-hero-inner">
          <div className="stays-kannada-mark" aria-hidden="true">
            <span />
            <span className="stays-mark-diamond">✦</span>
            <span />
          </div>

          <div className="stays-eyebrow">
            <Sparkles size={15} />
            YOUR JOURNEY, YOUR KIND OF STAY
          </div>

          <h1>
            Discover stays.
            <br />
            <span>Experience Karnataka.</span>
          </h1>

          <p className="stays-hero-copy">
            From heritage hideaways to peaceful homestays, find a place that
            belongs in your Karnataka story.
          </p>

          {journeyConfig && (
            <div className="stays-trip-summary">
              <div>
                <MapPin size={18} />
                <span>{destinations.join(' · ') || 'Your destinations'}</span>
              </div>
              <div>
                <Wallet size={18} />
                <span>
                  {formatINR(Number(journeyConfig.totalBudget || 0))} total trip budget
                </span>
              </div>
              <div>
                <Hotel size={18} />
                <span>
                  {journeyConfig.travellerCount} traveller(s) ·{' '}
                  {journeyConfig.travelStyle}
                </span>
              </div>
            </div>
          )}

          
<button
  type="button"
  className="stays-primary"
  onClick={findStays}
  disabled={loading}
>
  {loading ? (
    <>
      <RefreshCw className="stays-spin" size={18} />
      Finding your stays...
    </>
  ) : (
    <>
      <Sparkles size={18} />
      Find my perfect stay
      <span className="stays-button-arrow">↗</span>
    </>
  )}
</button>

          <div className="stays-hero-note">
            <span /> Personalised recommendations
            <span className="stays-note-separator">✦</span>
            Budget-aware
            <span className="stays-note-separator">✦</span>
            Source-linked
          </div>
        </div>

        <div className="stays-hero-bottom-rule" aria-hidden="true">
          <span />
          <span>ಕರ್ನಾಟಕ</span>
          <span />
        </div>
      </section>

      {error && (
        <section className="stays-message stays-error" role="alert">
          <strong>We couldn't complete the search.</strong>
          <p>{error}</p>
          <button onClick={findStays}>Try again</button>
        </section>
      )}

      {loading && (
        <section className="stays-loading">
          <div className="stays-loader">
            <Hotel size={30} />
          </div>
          <div className="stays-eyebrow">A LITTLE EXPLORATION IN PROGRESS</div>
          <h2>Finding your Karnataka stay.</h2>
          <p>
            Researching properties and matching them to your travel style and budget.
          </p>
          <div className="stays-loading-line"><span /></div>
        </section>
      )}

      {data && !loading && (
        <section className="stays-results">
          <div className="stays-section-heading">
            <div>
              <div className="stays-eyebrow">CURATED FOR YOUR JOURNEY</div>
              <h2>Places to stay, <span>stories to make.</span></h2>
              <p>Explore the shortlist selected for your route and travel style.</p>
            </div>
            <div className="stays-result-count">
              <strong>{data.stays?.length || 0}</strong>
              <span>STAYS FOUND</span>
            </div>
          </div>

          {data.budget_summary && (
            <div className="stays-budget">
              <div className="stays-budget-icon"><Wallet size={23} /></div>
              <div>
                <div className="stays-budget-label">YOUR ACCOMMODATION ALLOWANCE</div>
                <strong>
                  {formatINR(
                    data.budget_summary.estimated_accommodation_budget_inr || 0
                  )}
                </strong>
                <p>
                  {data.budget_summary.budget_note ||
                    'This is an estimated allocation; transport, food and activities need their own budget.'}
                </p>
              </div>
            </div>
          )}

          {data.stays?.length ? (
            <div className="stays-grid">
              {data.stays.map((stay, index) => (
                <article className="stays-card" key={`${stay.name}-${index}`}>
                  <div className={`stays-card-art stays-art-${index % 4}`}>
                    <div className="stays-art-corner stays-art-corner-left" />
                    <div className="stays-art-corner stays-art-corner-right" />

                    <div className="stays-art-emblem">
                      <Hotel size={35} strokeWidth={1.4} />
                    </div>

                    <span className="stays-card-number">
                      STAY {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="stays-property-type">
                      {stay.property_type || 'Accommodation'}
                    </span>
                    <span className="stays-art-bottom">NAMMA PRAYANA</span>
                  </div>

                  <div className="stays-card-content">
                    <div className="stays-location">
                      <MapPin size={14} />
                      {stay.destination}
                    </div>

                    <h3>{stay.name}</h3>
                    <p className="stays-description">{stay.description}</p>

                    <div className="stays-price">
                      <div>
                        <span className="stays-small-label">PRICE INDICATION</span>
                        <strong>{getPriceLabel(stay)}</strong>
                      </div>
                      <div className="stays-rating">
                        {stay.rating != null ? (
                          <>
                            <Star size={15} fill="currentColor" />
                            <strong>{stay.rating}/5</strong>
                          </>
                        ) : (
                          <span>Rating unverified</span>
                        )}
                      </div>
                    </div>

                    {stay.rating_source && (
                      <p className="stays-source-note">
                        Rating source: {stay.rating_source}
                      </p>
                    )}

                    {stay.amenities?.length > 0 && (
                      <div className="stays-amenities">
                        {stay.amenities.slice(0, 5).map((amenity) => (
                          <span key={amenity}>{amenity}</span>
                        ))}
                      </div>
                    )}

                    {stay.why_recommended && (
                      <div className="stays-why">
                        <Sparkles size={16} />
                        <div>
                          <span>WHY THIS STAY</span>
                          <p>{stay.why_recommended}</p>
                        </div>
                      </div>
                    )}

                    <div className="stays-card-links">
                      {stay.source_url && (
                        <a href={stay.source_url} target="_blank" rel="noreferrer">
                          Source <ExternalLink size={14} />
                        </a>
                      )}

                      {stay.phone && (
                        <a href={`tel:${stay.phone}`}>
                          <Phone size={14} /> Contact
                        </a>
                      )}

                      {stay.booking_url && (
                        <a
                          className="stays-book-link"
                          href={stay.booking_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          View stay <ExternalLink size={14} />
                        </a>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="stays-empty stays-no-results">
              <div><Hotel size={30} /></div>
              <h2>No suitable stays found yet.</h2>
              <p>Try another destination or review your trip budget.</p>
              <button className="stays-secondary" onClick={findStays}>
                <RefreshCw size={16} /> Search again
              </button>
            </div>
          )}

          <div className="stays-disclaimer">
            <span className="stays-disclaimer-mark">!</span>
            <p>
              {data.research_note} Prices, ratings and availability can change.
              Confirm room occupancy, final rates and cancellation terms with the
              property or booking provider. These are recommendations, not bookings.
            </p>
          </div>
        </section>
      )}

      {!data && !loading && !error && (
        <section className="stays-empty">
          <div className="stays-empty-emblem"><Hotel size={30} /></div>
          <div className="stays-eyebrow">YOUR KARNATAKA STORY STARTS HERE</div>
          <h2>A beautiful journey deserves a beautiful stay.</h2>
          <p>
            Let your destinations, travel dates and budget guide your stay
            recommendations.
          </p>
          <span className="stays-empty-rule">✦ ━━━━━━━━━ ✦</span>
        </section>
      )}

      <footer className="stays-footer">
        <div className="stays-footer-rule"><span /></div>
        <div className="stays-footer-brand">NAMMA<span>PRAYANA</span></div>
        <p>ನಾಡು · ನುಡಿ · ಸಂಸ್ಕೃತಿ · ಕರ್ನಾಟಕ</p>
        <small>DISCOVER KARNATAKA, YOUR WAY.</small>
      </footer>
    </main>
  );
}

