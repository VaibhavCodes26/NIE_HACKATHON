
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CalendarDays,
  CloudSun,
  Loader2,
  MapPin,
  Clock3,
  CloudRain,
  ArrowRight,
  Hotel,
  Utensils,
  Map,
  Check,
  MapPinned,
  Languages,
} from 'lucide-react';
import TrainSearchPanel from './components/TrainSearchPanel';
import HeroSection from './components/HeroSection';
import RoutePlanner from './components/RoutePlanner';
import TransportOptions from './components/TransportOptions';
import RouteDetailsPanel from './components/RouteDetailsPanel';
import { HeritageBorder } from './components/Motifs';
import { getRouteOptions } from './services/routeService';
import './route-discovery.css';

const ROUTE_DISCOVERY_STATE_KEY = 'np_route_discovery_state';

function getSavedRouteDiscoveryState() {
  try {
    const saved = sessionStorage.getItem(ROUTE_DISCOVERY_STATE_KEY);
    return saved ? JSON.parse(saved) : {};
  } catch (error) {
    console.error('Unable to restore route discovery state:', error);
    return {};
  }
}
const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

const EMPTY_DESTINATIONS = [];

const PLAN_DESTINATION_DETAILS = {
  badami: {
    id: 'badami',
    name: 'Badami',
    slug: 'badami',
    lat: 15.9149,
    lng: 75.6768,
  },
  hampi: {
    id: 'hampi',
    name: 'Hampi',
    slug: 'hampi',
    lat: 15.335,
    lng: 76.46,
  },
  mysuru: {
    id: 'mysuru',
    name: 'Mysuru',
    slug: 'mysuru',
    lat: 12.2958,
    lng: 76.6394,
  },
  bengaluru: {
    id: 'bengaluru',
    name: 'Bengaluru',
    slug: 'bengaluru',
    lat: 12.9716,
    lng: 77.5946,
  },
  coorg: {
    id: 'coorg',
    name: 'Coorg (Madikeri)',
    slug: 'coorg',
    lat: 12.4244,
    lng: 75.7382,
  },
  chikkamagaluru: {
    id: 'chikkamagaluru',
    name: 'Chikkamagaluru',
    slug: 'chikkamagaluru',
    lat: 13.3161,
    lng: 75.772,
  },
  mangaluru: {
    id: 'mangaluru',
    name: 'Mangaluru',
    slug: 'mangaluru',
    lat: 12.9141,
    lng: 74.856,
  },
  udupi: {
    id: 'udupi',
    name: 'Udupi',
    slug: 'udupi',
    lat: 13.3409,
    lng: 74.7421,
  },
  gokarna: {
    id: 'gokarna',
    name: 'Gokarna',
    slug: 'gokarna',
    lat: 14.5479,
    lng: 74.3188,
  },
  dandeli: {
    id: 'dandeli',
    name: 'Dandeli',
    slug: 'dandeli',
    lat: 15.247,
    lng: 74.629,
  },
  shivamogga: {
    id: 'shivamogga',
    name: 'Shivamogga',
    slug: 'shivamogga',
    lat: 13.9299,
    lng: 75.5681,
  },
  'belur-halebidu': {
    id: 'belur-halebidu',
    name: 'Belur & Halebidu',
    slug: 'belur-halebidu',
    lat: 13.1631,
    lng: 75.865,
  },
  vijayapura: {
    id: 'vijayapura',
    name: 'Vijayapura',
    slug: 'vijayapura',
    lat: 16.8302,
    lng: 75.71,
  },
  bidar: {
    id: 'bidar',
    name: 'Bidar',
    slug: 'bidar',
    lat: 17.9149,
    lng: 77.5046,
  },
  chitradurga: {
    id: 'chitradurga',
    name: 'Chitradurga',
    slug: 'chitradurga',
    lat: 14.2251,
    lng: 76.398,
  },
  belagavi: {
    id: 'belagavi',
    name: 'Belagavi',
    slug: 'belagavi',
    lat: 15.8497,
    lng: 74.4977,
  },
  hubballi: {
    id: 'hubballi',
    name: 'Hubballi',
    slug: 'hubballi',
    lat: 15.3647,
    lng: 75.124,
  },
  hassan: {
    id: 'hassan',
    name: 'Hassan',
    slug: 'hassan',
    lat: 13.0033,
    lng: 76.1004,
  },
};

const DEFAULT_TOURISM_DESTINATION = PLAN_DESTINATION_DETAILS.bengaluru;

function getLocalDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}

function resolveTourismDestination(destination) {
  if (!destination) return null;

  const id =
    typeof destination === 'string'
      ? destination
      : destination.id;

  if (!id) return null;

  const known = PLAN_DESTINATION_DETAILS[id];

  if (known) return known;

  const name =
    typeof destination === 'string'
      ? destination.replaceAll('-', ' ')
      : destination.name || id.replaceAll('-', ' ');

  return {
    id,
    name,
    slug: id,
    lat:
      typeof destination === 'object'
        ? destination.lat ?? null
        : null,
    lng:
      typeof destination === 'object'
        ? destination.lng ?? null
        : null,
  };
}

function getWeatherDescription(code) {
  if (code === 0) return 'Clear sky';
  if ([1, 2].includes(code)) return 'Mainly clear / partly cloudy';
  if (code === 3) return 'Overcast';
  if ([45, 48].includes(code)) return 'Foggy';
  if ([51, 53, 55, 56, 57].includes(code)) return 'Drizzle';
  if ([61, 63, 65, 66, 67].includes(code)) return 'Rain';
  if ([71, 73, 75, 77].includes(code)) return 'Snow / snow grains';
  if ([80, 81, 82].includes(code)) return 'Rain showers';
  if ([85, 86].includes(code)) return 'Snow showers';
  if ([95, 96, 99].includes(code)) return 'Thunderstorm';

  return 'Conditions unavailable';
}

export default function RouteDiscoveryPage({
  journeyConfig = null,
  onContinue,
  onOpenStays,
  initialDestinations = EMPTY_DESTINATIONS,
  initialStartDate,
  initialEndDate,
  initialFrom = null,
  initialTo = null,
  onOpenItinerary,
  onOpenSahayak,

}) {
  const effectiveConfig = useMemo(() => {
    if (journeyConfig) return journeyConfig;
    try {
      const saved = sessionStorage.getItem('np_journey_config');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  }, [journeyConfig]);

  const [from, setFrom] = useState( () => getSavedRouteDiscoveryState().from ?? initialFrom);
  const [to, setTo] = useState( () => getSavedRouteDiscoveryState().to ?? initialTo);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [routes, setRoutes] = useState(() => getSavedRouteDiscoveryState().routes ?? null);
  const [selected, setSelected] = useState(() => getSavedRouteDiscoveryState().selected ?? null);

  
const [startDate, setStartDate] = useState(
  () =>
    getSavedRouteDiscoveryState().startDate ||
    initialStartDate ||
    getLocalDateString()
);

const [tripDays, setTripDays] = useState(() => {
  const saved = getSavedRouteDiscoveryState();

  if (saved.tripDays) return saved.tripDays;

  if (!initialStartDate || !initialEndDate) return 1;

  const start = new Date(`${initialStartDate}T12:00:00`);
  const end = new Date(`${initialEndDate}T12:00:00`);

  return Math.max(
    1,
    Math.min(7, Math.floor((end - start) / 86400000) + 1)
  );
});
  // Resolve all selected destinations while keeping their order.
  // Restore the cities selected in Plan Your Journey.
const tourismDestinations = useMemo(() => {
  const savedDestinations =
    getSavedRouteDiscoveryState().destinations ?? [];

  const incoming =
    Array.isArray(initialDestinations) &&
    initialDestinations.length > 0
      ? initialDestinations
      : savedDestinations;

  const resolved = incoming
    .map(resolveTourismDestination)
    .filter(Boolean);

  return resolved.filter(
    (destination, index, all) =>
      all.findIndex((item) => item.id === destination.id) === index
  );
}, [initialDestinations]);
const [activeDestinationId, setActiveDestinationId] = useState(() => {
  const saved = getSavedRouteDiscoveryState();

  return (
    saved.activeDestinationId ||
    initialDestinations?.[0]?.id ||
    initialDestinations?.[0] ||
    saved.destinations?.[0] ||
    null
  );
});

  const [attractionsByDestination, setAttractionsByDestination] =
    useState({});

  const [loadingByDestination, setLoadingByDestination] =
    useState({});

  const [errorsByDestination, setErrorsByDestination] =
    useState({});

  const [selectedAttractionIds, setSelectedAttractionIds] = useState(
  
    () => getSavedRouteDiscoveryState().selectedAttractionIds ?? []);

  const [weatherByDay, setWeatherByDay] = useState({});
  const [weatherLoadingDay, setWeatherLoadingDay] = useState(null);
  const [weatherErrors, setWeatherErrors] = useState({});

  const transportRef = useRef(null);
  const detailsRef = useRef(null);

  const tourismDestination =
    tourismDestinations.find(
      (destination) => destination.id === activeDestinationId
    ) ||
    tourismDestinations[0] ||
    DEFAULT_TOURISM_DESTINATION;

  const attractions =
    attractionsByDestination[tourismDestination.id] || [];

  const attractionsLoading = Boolean(
    loadingByDestination[tourismDestination.id]
  );

  const attractionsError =
    errorsByDestination[tourismDestination.id] || '';

  // Return the selected attraction records from every loaded city.
  const selectedAttractions = useMemo(() => {
    const selectedIds = new Set(selectedAttractionIds);

    return tourismDestinations.flatMap((destination) =>
      (attractionsByDestination[destination.id] || []).filter(
        (attraction) => selectedIds.has(Number(attraction.id))
      )
    );
  }, [
    tourismDestinations,
    attractionsByDestination,
    selectedAttractionIds,
  ]);

  const endDate = useMemo(() => {
    const end = new Date(`${startDate}T12:00:00`);
    end.setDate(end.getDate() + tripDays - 1);

    return getLocalDateString(end);
  }, [startDate, tripDays]);
  
useEffect(() => {
  try {
    sessionStorage.setItem(
      'np_route_discovery_state',
      JSON.stringify({
        from,
        to,
        routes,
        selected,
        startDate,
        tripDays,
        activeDestinationId,
        selectedAttractionIds,
        weatherByDay,
        destinations: tourismDestinations.map(
  (destination) => destination.id
),
tourismDestinations,
      })
    );
  } catch (error) {
    console.error('Unable to save route discovery state:', error);
  }
}, [
  from,
  to,
  routes,
  selected,
  startDate,
  tripDays,
  activeDestinationId,
  selectedAttractionIds,
  weatherByDay,
]);


  const resetResults = () => {
    setRoutes(null);
    setSelected(null);
  };

  const handleFrom = (value) => {
    setFrom(value);

    setErrors((current) => ({
      ...current,
      from: undefined,
      same: undefined,
      route: undefined,
    }));

    resetResults();
  };

  const handleTo = (value) => {
    setTo(value);

    setErrors((current) => ({
      ...current,
      to: undefined,
      same: undefined,
      route: undefined,
    }));

    resetResults();
  };

  const swap = () => {
    setFrom(to);
    setTo(from);
    setErrors({});
    resetResults();
  };

  const scrollTo = (ref) =>
    requestAnimationFrame(() =>
      ref.current?.scrollIntoView({
        behavior: window.matchMedia?.(
          '(prefers-reduced-motion: reduce)'
        ).matches
          ? 'auto'
          : 'smooth',
        block: 'start',
      })
    );

  const explore = useCallback(async () => {
    const nextErrors = {};

    if (!from) {
      nextErrors.from = 'Please choose a starting point.';
    }

    if (!to) {
      nextErrors.to = 'Please choose a destination.';
    }

    if (from && to && from.id === to.id) {
      nextErrors.same =
        'Starting point and destination are the same. Please choose different places.';
    }

    setErrors(nextErrors);

    if (Object.keys(nextErrors).length) return;

    setLoading(true);

    try {
      const data = await getRouteOptions(from, to);

      setRoutes(data);
      setSelected(null);
      scrollTo(transportRef);
    } catch (error) {
      console.error('Unable to load route options:', error);

      setErrors((current) => ({
        ...current,
        route: 'Unable to calculate route options. Please try again.',
      }));
    } finally {
      setLoading(false);
    }
  }, [from, to]);

  const selectMode = (id) => {
    // Clicking the currently open route closes it.
    if (selected === id) {
      setSelected(null);
      return;
    }

    // Open the newly selected route.
    setSelected(id);
    scrollTo(detailsRef);
  };
  // Keep the active destination tab valid.
  useEffect(() => {
    if (
      !tourismDestinations.some(
        (destination) => destination.id === activeDestinationId
      )
    ) {
      setActiveDestinationId(
        tourismDestinations[0]?.id || 'bengaluru'
      );
    }
  }, [tourismDestinations, activeDestinationId]);

  // Fetch real attraction records for every selected destination.
  useEffect(() => {
    let cancelled = false;

    async function loadAllAttractions() {
      setLoadingByDestination(
        Object.fromEntries(
          tourismDestinations.map((destination) => [
            destination.id,
            true,
          ])
        )
      );

      setErrorsByDestination({});

      const results = await Promise.all(
        tourismDestinations.map(async (destination) => {
          try {
            if (!destination.slug) {
              throw new Error(
                `No database destination ID is configured for ${destination.name}.`
              );
            }

            const response = await fetch(
              `${API_BASE}/api/destinations/${encodeURIComponent(
                destination.slug
              )}/attractions`
            );

            if (!response.ok) {
              throw new Error(
                response.status === 404
                  ? `No attractions were found for ${destination.name}.`
                  : `Attractions request failed (${response.status}).`
              );
            }

            const data = await response.json();

            if (!Array.isArray(data)) {
              throw new Error(
                'The attractions API returned an unexpected response.'
              );
            }

            const sorted = [...data].sort(
              (a, b) =>
                Number(Boolean(b.is_must_visit)) -
                  Number(Boolean(a.is_must_visit)) ||
                Number(a.visit_order || 0) -
                  Number(b.visit_order || 0)
            );

            return {
              id: destination.id,
              attractions: sorted,
              error: '',
            };
          } catch (error) {
            return {
              id: destination.id,
              attractions: [],
              error: `${error.message} Check that the FastAPI backend is running.`,
            };
          }
        })
      );

      if (cancelled) return;

      const nextAttractions = {};
      const nextErrors = {};

      for (const result of results) {
        nextAttractions[result.id] = result.attractions;

        if (result.error) {
          nextErrors[result.id] = result.error;
        }
      }

      setAttractionsByDestination(nextAttractions);
      setErrorsByDestination(nextErrors);
      setLoadingByDestination({});
    }

    loadAllAttractions();

    return () => {
      cancelled = true;
    };
  }, [tourismDestinations]);

  const toggleAttraction = (attractionId) => {
    const id = Number(attractionId);

    setSelectedAttractionIds((current) =>
      current.includes(id)
        ? current.filter((existingId) => existingId !== id)
        : [...current, id]
    );
  };

  const checkWeather = async (dayIndex) => {
    if (!tourismDestination?.lat || !tourismDestination?.lng) {
      setWeatherErrors((current) => ({
        ...current,
        [dayIndex]:
          'Weather coordinates are unavailable for this destination.',
      }));

      return;
    }

    const date = new Date(`${startDate}T12:00:00`);
    date.setDate(date.getDate() + dayIndex);

    const targetDate = getLocalDateString(date);

    setWeatherLoadingDay(dayIndex);

    setWeatherErrors((current) => ({
      ...current,
      [dayIndex]: undefined,
    }));

    try {
      const params = new URLSearchParams({
        latitude: String(tourismDestination.lat),
        longitude: String(tourismDestination.lng),
        daily:
          'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
        timezone: 'auto',
        start_date: targetDate,
        end_date: targetDate,
      });

      const response = await fetch(
        `https://api.open-meteo.com/v1/forecast?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(
          'Forecast unavailable for this date. Try a date within the forecast provider’s supported range.'
        );
      }

      const data = await response.json();

      if (!data.daily?.time?.length) {
        throw new Error(
          'No forecast data was returned for this date.'
        );
      }

      setWeatherByDay((current) => ({
        ...current,
        [dayIndex]: {
          date: data.daily.time[0],
          description: getWeatherDescription(
            data.daily.weather_code?.[0]
          ),
          high: data.daily.temperature_2m_max?.[0],
          low: data.daily.temperature_2m_min?.[0],
          rain: data.daily.precipitation_probability_max?.[0],
        },
      }));
    } catch (error) {
      setWeatherErrors((current) => ({
        ...current,
        [dayIndex]:
          error.message || 'Unable to load the weather forecast.',
      }));
    } finally {
      setWeatherLoadingDay(null);
    }
  };

// Save selected attractions and open the itinerary page.
const saveItinerarySelection = () => {
  if (selectedAttractionIds.length === 0) {
    window.alert('Please select at least one tourist spot first.');
    return;
  }

  const payload = {
    destinations: tourismDestinations.map(
      (destination) => destination.id
    ),
    selected_attraction_ids: Array.from(new Set(selectedAttractionIds.map(Number))),
    start_date: startDate,
    end_date: endDate,
    trip_days: tripDays,
    traveller_count: Number(
      effectiveConfig?.travellerCount ??
      effectiveConfig?.traveller_count ??
      3
    ),
    travel_style:
      effectiveConfig?.travelStyle ??
      effectiveConfig?.travel_style ??
      'premium',
    total_budget: Number(
      effectiveConfig?.totalBudget ??
      effectiveConfig?.total_budget ??
      10000
    ),
    interests:
      effectiveConfig?.interests ?? [
        'Heritage & culture',
        'Local food',
      ],
    selected_places: selectedAttractions.map((place) => ({
      id: Number(place.id),
      destination_id: place.destination_id,
      name: place.name,
    })),
  };

  try {
    sessionStorage.setItem(
      'np_selected_itinerary',
      JSON.stringify(payload)
    );
    sessionStorage.setItem(
      'np_journey_config',
      JSON.stringify({
        ...effectiveConfig,
        destinations: payload.destinations,
        startDate: payload.start_date,
        endDate: payload.end_date,
        travellerCount: payload.traveller_count,
        travelStyle: payload.travel_style,
        totalBudget: payload.total_budget,
        interests: payload.interests,
      })
    );

    if (typeof onOpenItinerary === 'function') {
      onOpenItinerary(payload.selected_attraction_ids);
    } else {
      console.error('onOpenItinerary callback was not provided.');
      window.alert('Itinerary navigation is not configured yet.');
    }
  } catch (error) {
    console.error('Unable to save itinerary selection:', error);
    window.alert('Unable to save your selections. Please try again.');
  }
};


  return (
    <div className="rd-page">
      <HeroSection />
      <HeritageBorder className="rd-divider" />

      <RoutePlanner
        from={from}
        to={to}
        errors={errors}
        loading={loading}
        onFromChange={handleFrom}
        onToChange={handleTo}
        onSwap={swap}
        onSubmit={explore}
      />

      {errors.route && (
        <p className="rd-planner__error" role="alert">
          {errors.route}
        </p>
      )}

      {routes && from && to && (
        <>
          <div ref={transportRef} className="rd-reveal">
            <TransportOptions
              routes={routes}
              selected={selected}
              onSelect={selectMode}
              from={from}
              to={to}
            />
          </div>

{selected === 'train' && (
  <div ref={detailsRef} className="rd-reveal">
    <TrainSearchPanel />
  </div>
)}

{selected && selected !== 'train' && (
  <div ref={detailsRef} className="rd-reveal">
    <RouteDetailsPanel
      modeId={selected}
      routes={routes}
      from={from}
      to={to}
      onContinue={onContinue}
    />
  </div>
)}
        </>
      )}

      {/* Multi-city tourism discovery and attraction selection */}
      <section
        className="rd-tourism rd-reveal"
        aria-labelledby="rd-tourism-title"
      >
        <div className="rd-container">
          <div className="rd-tourism__heading">
            <span className="rd-tourism__eyebrow">
              <MapPin size={15} /> Explore Karnataka
            </span>

            <h2 id="rd-tourism-title">
              Your Karnataka Discovery
            </h2>

            <p>
              Explore each selected city, choose the places you want to
              visit, and build your itinerary from real database attractions.
            </p>
          </div>

          <div className="rd-tourism__controls">
            <label className="rd-tourism__field">
              <span>
                <CalendarDays size={16} /> Journey starts
              </span>

              <input
                type="date"
                value={startDate}
                min={getLocalDateString()}
                onChange={(event) => {
                  setStartDate(event.target.value);
                  setWeatherByDay({});
                  setWeatherErrors({});
                }}
              />
            </label>

            <label className="rd-tourism__field">
              <span>Number of days</span>

              <select
                value={tripDays}
                onChange={(event) => {
                  setTripDays(Number(event.target.value));
                  setWeatherByDay({});
                  setWeatherErrors({});
                }}
              >
                {[1, 2, 3, 4, 5, 6, 7].map((days) => (
                  <option key={days} value={days}>
                    {days} {days === 1 ? 'day' : 'days'}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="rd-tourism__summary">
            <span>
              {tourismDestinations.length}{' '}
              {tourismDestinations.length === 1
                ? 'destination'
                : 'destinations'}{' '}
              selected
            </span>

            <span>
              {selectedAttractionIds.length} places selected
            </span>
          </div>

          {/* Destination tabs */}
          <div
            className="rd-city-tabs"
            role="tablist"
            aria-label="Selected destinations"
          >
            {tourismDestinations.map((destination) => {
              const active =
                destination.id === tourismDestination.id;

              const cityAttractions =
                attractionsByDestination[destination.id] || [];

              const selectedCount = cityAttractions.filter((place) =>
                selectedAttractionIds.includes(Number(place.id))
              ).length;

              return (
                <button
                  key={destination.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={`rd-city-tab${
                    active ? ' is-active' : ''
                  }`}
                  onClick={() =>
                    setActiveDestinationId(destination.id)
                  }
                >
                  <MapPin size={15} />
                  <span>{destination.name}</span>
                  <small>{selectedCount}</small>
                </button>
              );
            })}
          </div>

          {/* Attractions for the currently active destination */}
          <div className="rd-city-attractions">
            <div className="rd-city-attractions__heading">
              <div>
                <span className="rd-tourism__eyebrow">
                  <MapPinned size={15} /> Destination highlights
                </span>

                <h3>{tourismDestination.name}</h3>

                <p>
                  Select the actual tourist spots you want included.
                </p>
              </div>
            </div>

            {attractionsLoading && (
              <div className="rd-tourism__status">
                <Loader2 className="rd-spin" size={21} />
                Loading {tourismDestination.name} attractions…
              </div>
            )}

            {!attractionsLoading && attractionsError && (
              <div className="rd-tourism__notice" role="alert">
                {attractionsError}
              </div>
            )}

            {!attractionsLoading &&
              !attractionsError &&
              attractions.length === 0 && (
                <div className="rd-tourism__notice">
                  No tourist spots are currently available in the
                  database for {tourismDestination.name}.
                </div>
              )}

            {!attractionsLoading &&
              !attractionsError &&
              attractions.length > 0 && (
                <div className="rd-attraction-grid">
                  {attractions.map((place) => {
                    const id = Number(place.id);

                    const isChecked =
                      selectedAttractionIds.includes(id);

                    return (
                      <label
                        key={place.id}
                        className={`rd-attraction-card${
                          isChecked ? ' is-selected' : ''
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleAttraction(place.id)}
                          aria-label={`Select ${place.name}`}
                        />

                        <span className="rd-attraction-card__check">
                          {isChecked && <Check size={16} />}
                        </span>

                        <div className="rd-attraction-card__body">
                          <div className="rd-attraction-card__badges">
                            {place.is_must_visit && (
                              <span className="rd-place__must">
                                Must Visit
                              </span>
                            )}

                            {place.category && (
                              <span className="rd-attraction-card__category">
                                {place.category}
                              </span>
                            )}
                          </div>

                          <h4>{place.name}</h4>

                          {place.description && (
                            <p>{place.description}</p>
                          )}

                          <div className="rd-place__meta">
                            {place.estimated_duration_minutes > 0 && (
                              <span>
                                <Clock3 size={13} />

                                {place.estimated_duration_minutes >= 60
                                  ? `${Math.floor(
                                      place.estimated_duration_minutes / 60
                                    )}h${
                                      place.estimated_duration_minutes % 60
                                        ? ` ${
                                            place.estimated_duration_minutes % 60
                                          }m`
                                        : ''
                                    }`
                                  : `${place.estimated_duration_minutes} min`}
                              </span>
                            )}

                            {place.suggested_time && (
                              <span>{place.suggested_time}</span>
                            )}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
          </div>
        </div>
      </section>

      {/* Keep only the three existing navigation buttons */}
      <section
        className="rd-quick-nav"
        aria-label="Explore travel options"
      >
        <div className="rd-container">
          <a
            className="rd-quick-nav__item rd-quick-nav__item--primary"
            href="/food-spots"
          >
            <span className="rd-quick-nav__icon">
              <Utensils size={23} />
            </span>

            <span className="rd-quick-nav__text">
              <strong>Food Spots</strong>
              <small>Discover local flavours</small>
            </span>

            <ArrowRight
              className="rd-quick-nav__arrow"
              size={19}
            />
          </a>

          <button
            type="button"
            className="rd-quick-nav__item rd-quick-nav__item--primary"
            onClick={onOpenStays}
          >
            <span className="rd-quick-nav__icon">
              <Hotel size={23} />
            </span>

            <span className="rd-quick-nav__text">
              <strong>Stays</strong>
              <small>Find your ideal stay</small>
            </span>

            <ArrowRight
              className="rd-quick-nav__arrow"
              size={19}
            />
          </button>

          <button
            type="button"
            className="rd-quick-nav__item rd-quick-nav__item--primary"
            onClick={saveItinerarySelection}
            
          >
            <span className="rd-quick-nav__icon">
              <Map size={23} />
            </span>

            <span className="rd-quick-nav__text">
              <strong>Get Your Itinerary</strong>
              <small>Build your Karnataka journey</small>
            </span>
            
            <ArrowRight
              className="rd-quick-nav__arrow"
              size={19}
            />
          </button>
        </div>
      </section>

      <HeritageBorder className="rd-divider rd-divider--end" />
    </div>
  );
}

