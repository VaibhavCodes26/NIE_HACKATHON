
import { useEffect, useState } from 'react';
import {
  ArrowDown,
  ArrowRight,
  ChefHat,
  MapPin,
  Utensils,
  LoaderCircle,
  Search,
  Star,
} from 'lucide-react';

import './FoodSpots.css';

const goToPage = (path) => {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
  window.scrollTo({ top: 0, behavior: 'auto' });
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function FoodSpots() {
  const [cities, setCities] = useState([]);
  const [selectedCity, setSelectedCity] = useState('');
  const [foods, setFoods] = useState([]);
  const [loadingCities, setLoadingCities] = useState(true);
  const [loadingFoods, setLoadingFoods] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    async function loadCities() {
      try {
        setLoadingCities(true);
        setError('');

        const response = await fetch(`${API_BASE}/api/food/cities`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error('Could not load cities. Please try again.');
        }

        const data = await response.json();
        const cityList = Array.isArray(data) ? data : data.cities || [];

        setCities(cityList);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Unable to load cities.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingCities(false);
        }
      }
    }

    loadCities();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedCity) {
      setFoods([]);
      return;
    }

    const controller = new AbortController();

    async function loadFoods() {
      try {
        setLoadingFoods(true);
        setError('');
        setFoods([]);

        const params = new URLSearchParams({ city: selectedCity });
        const response = await fetch(
          `${API_BASE}/api/food/spots?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error('Could not load food spots for this city.');
        }

        const data = await response.json();
        setFoods(Array.isArray(data) ? data : data.foods || []);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Unable to load food recommendations.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingFoods(false);
        }
      }
    }

    loadFoods();
    return () => controller.abort();
  }, [selectedCity]);

  return (
    <main className="fs-page">
      <div className="foodspots-navigation">
        <button
          type="button"
          className="foodspots-nav-btn foodspots-home-btn"
          onClick={() => goToPage('/')}
        >
          <span aria-hidden="true">⌂</span>
          Home
        </button>

        <button
          type="button"
          className="foodspots-nav-btn foodspots-back-btn"
          onClick={() => goToPage('/route-discovery')}
        >
          <span aria-hidden="true">←</span>
          Back to Route Discovery
        </button>
      </div>

      <section className="fs-hero">
        <div className="fs-hero__ornament fs-hero__ornament--left" />
        <div className="fs-hero__ornament fs-hero__ornament--right" />

        <div className="fs-container fs-hero__content">
          <div className="fs-eyebrow">
            <span className="fs-eyebrow__line" />
            <Utensils size={16} />
            A Taste of Karnataka
            <span className="fs-eyebrow__line" />
          </div>

          <h1>
            Every City Has a Story.
            <br />
            <span>Every Plate Tells One.</span>
          </h1>

          <p className="fs-hero__description">
            From the comforting aroma of a Bengaluru dosa to the rich
            flavours of coastal Karnataka, discover the dishes, local
            favourites, and food traditions that make every journey special.
          </p>

          <a className="fs-hero__cta" href="#fs-discover">
            Discover Local Food
            <ArrowDown size={18} />
          </a>

          <div className="fs-hero__signature">
            <span />
            ಕರ್ನಾಟಕದ ರುಚಿ
            <span />
          </div>
        </div>
      </section>

      <section className="fs-discover" id="fs-discover">
        <div className="fs-container">
          <header className="fs-section-heading">
            <span className="fs-section-heading__eyebrow">
              <MapPin size={15} />
              YOUR CULINARY JOURNEY
            </span>

            <h2>What Are We Tasting Today?</h2>

            <p>
              Choose the city you are exploring. Discover its local
              specialities and food spots from our curated database.
            </p>
          </header>

          <div className="fs-city-panel">
            <div className="fs-city-panel__icon">
              <MapPin size={24} />
            </div>

            <div className="fs-city-panel__field">
              <label htmlFor="fs-city-select">
                Select your exploring city
              </label>

              <div className="fs-select-wrap">
                <select
                  id="fs-city-select"
                  value={selectedCity}
                  onChange={(event) => setSelectedCity(event.target.value)}
                  disabled={loadingCities}
                >
                  <option value="">
                    {loadingCities
                      ? 'Loading cities…'
                      : 'Choose a city in Karnataka'}
                  </option>

                  {cities.map((city) => {
                    const name = typeof city === 'string' ? city : city.name;

                    return (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    );
                  })}
                </select>
                <ArrowDown size={17} />
              </div>
            </div>

            <div className="fs-city-panel__badge">
              <ChefHat size={17} />
              Local flavours
            </div>
          </div>

          {error && (
            <div className="fs-state fs-state--error" role="alert">
              <p>{error}</p>
              <button
                type="button"
                onClick={() => setSelectedCity((city) => `${city} `.trim())}
              >
                Try again
              </button>
            </div>
          )}

          {!selectedCity && !loadingCities && !error && (
            <div className="fs-empty">
              <div className="fs-empty__icon">
                <Search size={28} />
              </div>
              <h3>Your food adventure starts here</h3>
              <p>
                Select a city above to uncover its signature dishes and places
                to eat.
              </p>
            </div>
          )}

          {loadingFoods && (
            <div className="fs-state">
              <LoaderCircle className="fs-spin" size={30} />
              <p>Discovering the flavours of {selectedCity}…</p>
            </div>
          )}

          {!loadingFoods &&
            selectedCity &&
            !error &&
            foods.length === 0 && (
              <div className="fs-empty">
                <div className="fs-empty__icon">
                  <Utensils size={28} />
                </div>
                <h3>More flavours coming soon</h3>
                <p>
                  We don’t have food spots listed for {selectedCity} yet.
                  Check back as our local food database grows.
                </p>
              </div>
            )}

          {!loadingFoods && foods.length > 0 && !error && (
            <>
              <div className="fs-results-heading">
                <div>
                  <span className="fs-results-heading__eyebrow">
                    CURATED FOR YOU
                  </span>
                  <h3>Flavours of {selectedCity}</h3>
                </div>

                <span className="fs-results-count">
                  {foods.length} {foods.length === 1 ? 'spot' : 'spots'}
                </span>
              </div>

              <div className="fs-food-grid">
                {foods.map((food, index) => {
                  const restaurant =
                    food.famous_food_spot ||
                    food.restaurant_name ||
                    food.name ||
                    'Local Food Spot';

                  const dish =
                    food.speciality_dish || food.dish || '';

                  const attraction =
                    food.tourist_attraction || food.category || 'Local food';

                  const description =
                    food.description ||
                    'Discover this local favourite on your Karnataka journey.';

                  const imageUrl =
                    food.image_url || food.image || '';
                  console.log('FOOD IMAGE DEBUG:', {
                    restaurant,
                    image_url: food.image_url,
                    image: food.image,
                    imageUrl,
                  });

                  const mapsUrl =
                    food.google_maps_link ||
                    food.map_url ||
                    '';

                  const rating = food.rating_as_per_google;

                  return (
                    <article
                      className="fs-food-card"
                      key={food.spot_id ?? food.id ?? `${restaurant}-${index}`}
                    >

                      <div className="fs-food-card__image-wrap">
                        {/* Fallback stays underneath the image */}
                        <div className="fs-food-card__image-placeholder">
                          <Utensils size={34} />
                          <span>{dish || 'Karnataka Cuisine'}</span>
                        </div>

                        {imageUrl && (
                          <img
                            className="fs-food-card__image"
                            src={imageUrl}
                            alt={`${dish || 'Local Karnataka food'} at ${restaurant}`}
                            loading="lazy"
                            onError={(event) => {
                              event.currentTarget.style.display = 'none';
                            }}
                          />
                        )}

                        <div
                          className="fs-food-card__image-overlay"
                          aria-hidden="true"
                        />

                        <span className="fs-food-card__category">
                          {attraction || 'Local food'}
                        </span>

                        {food.is_must_try && (
                          <span className="fs-food-card__must">
                            Must try
                          </span>
                        )}

                        {dish && (
                          <h3 className="fs-food-card__image-title">
                            {dish}
                          </h3>
                        )}
                      </div>


                      <div className="fs-food-card__body">
                        <span className="fs-food-card__city">
                          <MapPin size={13} />
                          {food.city || selectedCity}
                        </span>

                        <h4>{restaurant}</h4>

                        {dish && (
                          <div className="fs-food-card__restaurant">
                            <ChefHat size={15} />
                            {dish}
                          </div>
                        )}

                        {rating && (
                          <div className="fs-food-card__price">
                            <Star size={14} />
                            {rating}
                          </div>
                        )}

                        <p>{description}</p>

                        {food.price_range && (
                          <span className="fs-food-card__price">
                            {food.price_range}
                          </span>
                        )}

                        {mapsUrl && (
                          <a
                            className="fs-food-card__link"
                            href={mapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Find this spot <ArrowRight size={16} />
                          </a>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </section>

      <div className="fs-bottom-border" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </main>
  );
}
