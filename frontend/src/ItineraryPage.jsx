
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronDown,
  Cloud,
  CloudRain,
  Compass,
  Hotel,
  MapPin,
  Moon,
  RefreshCw,
  Sparkles,
  Sun,
  Utensils,
  Wallet,
  Clock3,
  Users,
  Footprints,
  Heart,
  ShieldCheck,
  AlertTriangle,
  Coffee,
  Mountain,
} from "lucide-react";
import "./ItineraryPage.css";

const API_BASE = "http://127.0.0.1:8000";
const EMPTY_ARRAY = [];

const cityCoordinates = {
  bengaluru: { lat: 12.9716, lon: 77.5946 },
  bangalore: { lat: 12.9716, lon: 77.5946 },
  mysuru: { lat: 12.2958, lon: 76.6394 },
  mysore: { lat: 12.2958, lon: 76.6394 },
  hampi: { lat: 15.335, lon: 76.46 },
  badami: { lat: 15.9149, lon: 75.6768 },
  belagavi: { lat: 15.8497, lon: 74.4977 },
  hubballi: { lat: 15.3647, lon: 75.124 },
  hubli: { lat: 15.3647, lon: 75.124 },
  mangaluru: { lat: 12.9141, lon: 74.856 },
  mangalore: { lat: 12.9141, lon: 74.856 },
  udupi: { lat: 13.3409, lon: 74.7421 },
  gokarna: { lat: 14.5479, lon: 74.3188 },
  coorg: { lat: 12.3375, lon: 75.8069 },
  chikmagalur: { lat: 13.3161, lon: 75.772 },
  chikkamagaluru: { lat: 13.3161, lon: 75.772 },
  shivamogga: { lat: 13.9299, lon: 75.5681 },
  vijayapura: { lat: 16.8302, lon: 75.71 },
  bidar: { lat: 17.9133, lon: 77.5301 },
  chitradurga: { lat: 14.2251, lon: 76.398 },
  belur: { lat: 13.1629, lon: 75.8652 },
  hassan: { lat: 13.0068, lon: 76.0996 },
};

function normaliseCity(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ");
}

function cityLabel(value) {
  const name = String(value ?? "").replace(/[_-]/g, " ").trim();
  if (!name) return "Karnataka";
  return name.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  if (!value) return "Date not selected";
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function getDaysBetween(start, end) {
  if (!start || !end) return 1;
  const first = new Date(`${start}T12:00:00`);
  const last = new Date(`${end}T12:00:00`);
  const days = Math.round((last - first) / 86400000) + 1;
  return Math.max(1, Math.min(days || 1, 30));
}

function formatCurrency(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return `₹${Math.round(amount).toLocaleString("en-IN")}`;
}

function readDestinations(config) {
  const raw = config?.destinations ?? config?.selectedDestinations ?? [];
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item) => {
      if (typeof item === "string") return item;
      return item?.name ?? item?.city ?? item?.slug ?? item?.id ?? "";
    })
    .filter(Boolean);
}

function getDayItems(day) {
  return (
    day?.stops ??
    day?.activities ??
    day?.attractions ??
    day?.items ??
    day?.itinerary ??
    []
  );
}

function getStopName(stop) {
  if (typeof stop === "string") return stop;
  return (
    stop?.name ??
    stop?.attraction_name ??
    stop?.title ??
    stop?.activity ??
    "Explore at your own pace"
  );
}

function getStopTime(stop) {
  if (typeof stop === "string") return "";
  return stop?.time ?? stop?.start_time ?? stop?.suggested_time ?? "";
}

function getStopDescription(stop) {
  if (typeof stop === "string") return "";
  return stop?.description ?? stop?.notes ?? stop?.reason ?? "";
}

function getStopCost(stop) {
  if (typeof stop === "string") return null;
  return (
    stop?.estimated_cost ??
    stop?.estimatedCost ??
    stop?.cost ??
    stop?.price ??
    null
  );
}

function getWeatherIcon(description = "") {
  const text = String(description).toLowerCase();
  if (text.includes("rain") || text.includes("shower") || text.includes("storm")) {
    return CloudRain;
  }
  if (text.includes("cloud") || text.includes("overcast")) return Cloud;
  return Sun;
}


function readSavedItinerarySelection() {
  try {
    const saved = sessionStorage.getItem("np_selected_itinerary");
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}


export default function ItineraryPage({
  journeyConfig,
  selectedAttractionIds = EMPTY_ARRAY,
  initialItinerary = null,
  onBack,
  onModifyJourney,
}) {
 console.log("ITINERARY PAGE IS RUNNING");
const config = journeyConfig ?? {};

const [savedSelection] = useState(readSavedItinerarySelection);

const destinations = useMemo(
  () => readDestinations(config),
  [config]
);

const requestDestinations =
  Array.isArray(savedSelection?.destinations) &&
  savedSelection.destinations.length
    ? savedSelection.destinations
    : destinations;

const startDate =
  savedSelection?.start_date ||
  config.startDate ||
  config.start_date ||
  "";

const endDate =
  savedSelection?.end_date ||
  config.endDate ||
  config.end_date ||
  "";

const effectiveSelectedAttractionIds =
  Array.isArray(savedSelection?.selected_attraction_ids)
    ? savedSelection.selected_attraction_ids
    : selectedAttractionIds;

  const travellerCount = Number(
    config.travellerCount ?? config.traveller_count ?? config.travelers ?? 1
  );
  const travelStyle = config.travelStyle ?? config.travel_style ?? "comfortable";
  const totalBudget = Number(config.totalBudget ?? config.total_budget ?? 0);
  const interests = config.interests ?? EMPTY_ARRAY;

  const [itinerary, setItinerary] = useState(initialItinerary);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState("");
  const [activeDay, setActiveDay] = useState(0);
  const [activeWeatherCity, setActiveWeatherCity] = useState(destinations[0] ?? "");
  const [weatherByCity, setWeatherByCity] = useState({});
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState("");
  const [foodByCity, setFoodByCity] = useState({});
  const [foodLoading, setFoodLoading] = useState(false);
  const [foodError, setFoodError] = useState("");
  const [stays, setStays] = useState([]);
  const [staysLoading, setStaysLoading] = useState(false);
  const [staysError, setStaysError] = useState("");
  const [openSection, setOpenSection] = useState("food");
  const [showTravellerNeeds, setShowTravellerNeeds] = useState(false);
  const [travellerNeeds, setTravellerNeeds] = useState([]);
  const [specialNotes, setSpecialNotes] = useState("");
  const [adjustment, setAdjustment] = useState("balanced");
  const [adjustmentMessage, setAdjustmentMessage] = useState("");

  const durationDays = useMemo(
    () => getDaysBetween(startDate, endDate),
    [startDate, endDate]
  );

  useEffect(() => {
    if (!destinations.length) {
      setActiveWeatherCity("");
      return;
    }
    if (!destinations.includes(activeWeatherCity)) {
      setActiveWeatherCity(destinations[0]);
    }
  }, [destinations, activeWeatherCity]);

 
const generatePreview = useCallback(async (adjustmentRequest = "") => {
  if (!requestDestinations.length) {
    setPageError(
      "No destinations were carried forward. Go back and select at least one city."
    );
    return false;
  }

  setLoading(true);
  setPageError("");

  const payload = {
    destinations: requestDestinations,
    start_date: startDate,
    end_date: endDate,
    traveller_count: travellerCount || 1,
    travel_style: travelStyle,
    total_budget: totalBudget || 1000,
    interests: Array.isArray(interests) ? interests : [],
    selected_attraction_ids: effectiveSelectedAttractionIds,
    adjustment_request: adjustmentRequest,
  };

  console.log("Itinerary generation payload:", payload);

  try {
    const response = await fetch(
      `${API_BASE}/api/itineraries/generate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      const details = await response.text();
      throw new Error(details || `Request failed (${response.status})`);
    }

    const result = await response.json();

    setItinerary(result);
    setActiveDay(0);

    return true;
  } catch (error) {
    setPageError(
      `We couldn't generate the itinerary. ${
        error.message || "Check that the backend is running."
      }`
    );

    return false;
  } finally {
    setLoading(false);
  }
}, [
  requestDestinations,
  startDate,
  endDate,
  travellerCount,
  travelStyle,
  totalBudget,
  interests,
  effectiveSelectedAttractionIds,
]);


  useEffect(() => {
    if (initialItinerary) {
      setItinerary(initialItinerary);
      setActiveDay(0);
    }
  }, [initialItinerary]);

  const loadWeather = useCallback(async () => {
    if (!destinations.length) return;

    setWeatherLoading(true);
    setWeatherError("");

    const results = await Promise.all(
      destinations.map(async (city) => {
        try {
          const url = new URL(`${API_BASE}/api/weather/forecast`);
          url.searchParams.set("destination", city);
          if (startDate) url.searchParams.set("date", startDate);

          const response = await fetch(url);
          if (!response.ok) throw new Error(`Weather request failed (${response.status})`);
          return [city, await response.json()];
        } catch (error) {
          return [city, { _error: error.message }];
        }
      })
    );

    
    const next = Object.fromEntries(
      results.map(([city, value]) => {
        if (value?._error) {
          return [city, value];
        }

        // The forecast endpoint returns values inside daily[].
        const daily = Array.isArray(value?.daily)
          ? value.daily
          : [];

        const forecast =
          daily.find((item) => item.date === startDate) ??
          daily[0] ??
          {};

        const code = Number(forecast.weather_code);

        const description =
          ({
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            80: "Rain showers",
            81: "Moderate rain showers",
            82: "Heavy rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail",
          })[code] ?? "Weather forecast";

        return [
          city,
          {
            ...value,
            date: forecast.date ?? startDate,
            description,
            temperature:
              forecast.temperature_max_c != null &&
              forecast.temperature_min_c != null
                ? `${forecast.temperature_min_c}–${forecast.temperature_max_c}`
                : null,
            rain_probability:
              forecast.precipitation_probability_max ?? null,
            source: value?.source ?? "Open-Meteo",
            advice:
              forecast.precipitation_probability_max >= 40
                ? "Rain is possible. Carry an umbrella and keep outdoor plans flexible."
                : "Check local conditions before starting outdoor activities.",
          },
        ];
      })
    );

    setWeatherByCity(next);


    const failed = results.filter(([, value]) => value?._error);
    if (failed.length === results.length) {
      setWeatherError("Weather data is unavailable right now. Please try again later.");
    }
    setWeatherLoading(false);
  }, [destinations, startDate]);

  useEffect(() => {
    loadWeather();
  }, [loadWeather]);

  const loadFood = useCallback(async () => {
    if (!destinations.length) return;

    setFoodLoading(true);
    setFoodError("");

    const results = await Promise.all(
      destinations.map(async (city) => {
        try {
          const url = new URL(`${API_BASE}/api/food/spots`);
          url.searchParams.set("city", city);
          const response = await fetch(url);
          if (!response.ok) throw new Error(`Food request failed (${response.status})`);
          const result = await response.json();
          const items = Array.isArray(result)
           ? result
           : result?.foods ?? result?.spots ?? result?.food_spots ?? result?.items ?? [];
          return [city, items];
        } catch {
          return [city, null];
        }
      })
    );

    setFoodByCity(Object.fromEntries(results));
    if (results.every(([, items]) => items === null)) {
      setFoodError("Food recommendations could not be loaded from the database.");
    }
    setFoodLoading(false);
  }, [destinations]);

  useEffect(() => {
    loadFood();
  }, [loadFood]);

  const loadStays = useCallback(async () => {
    if (!destinations.length) return;

    setStaysLoading(true);
    setStaysError("");

    try {
      const response = await fetch(`${API_BASE}/api/stays/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          destinations,
          start_date: startDate || null,
          end_date: endDate || null,
          traveller_count: travellerCount || 1,
          travel_style: travelStyle,
          total_budget: totalBudget || null,
        }),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || `Request failed (${response.status})`);
      }

      const result = await response.json();
      const items = Array.isArray(result)
        ? result
        : result?.stays ?? result?.recommendations ?? result?.hotels ?? [];
      setStays(items);
    } catch (error) {
      setStaysError(error.message || "Stay recommendations are temporarily unavailable.");
    } finally {
      setStaysLoading(false);
    }
  }, [destinations, startDate, endDate, travellerCount, travelStyle, totalBudget]);

  useEffect(() => {
    loadStays();
  }, [loadStays]);

  const days = useMemo(() => {
    const source = itinerary?.days ?? itinerary?.itinerary_days ?? [];
    return Array.isArray(source) ? source : [];
  }, [itinerary]);

  const selectedDay = days[activeDay] ?? null;
  const selectedDayItems = selectedDay ? getDayItems(selectedDay) : [];

  const estimatedBudget =
    itinerary?.total_budget ??
    itinerary?.estimated_total_cost ??
    itinerary?.estimated_cost ??
    totalBudget;

  const weather = weatherByCity[activeWeatherCity];
  const weatherDescription =
    weather?.description ??
    weather?.condition ??
    weather?.advice ??
    weather?.summary ??
    "";
  const WeatherIcon = getWeatherIcon(weatherDescription);

  const activeFood = foodByCity[activeWeatherCity];
  const foodItems = Array.isArray(activeFood) ? activeFood : [];

  const toggleNeed = (value) => {
    setTravellerNeeds((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value]
    );
  };

const submitAdjustment = async () => {
  const request = [
    `Please revise the existing itinerary using this preference: ${adjustment}.`,
    travellerNeeds.length
      ? `Traveller considerations: ${travellerNeeds.join(", ")}.`
      : "",
    specialNotes.trim()
      ? `Additional request: ${specialNotes.trim()}.`
      : "",
    "Keep the same destinations, dates, budget, and selected attractions wherever feasible. Modify the schedule according to these preferences. Use supplied attraction, food, and weather records. Explain changes and any extra costs.",
  ]
    .filter(Boolean)
    .join(" ");

  setAdjustmentMessage("Applying your preferences…");
  setPageError("");

  try {
    await generatePreview(request);
    setAdjustmentMessage(
      "Preferences applied. Your itinerary has been updated."
    );
  } catch (error) {
    setAdjustmentMessage(
      `Couldn't apply preferences: ${error.message || "Please try again."}`
    );
  }
};

return (
  <main className="itinerary-page">
    <div className="itinerary-page__texture" aria-hidden="true" />

    <header className="itinerary-topbar">
      <button
        type="button"
        className="itinerary-back"
        onClick={onBack}
      >
        <ArrowLeft size={17} />
        <span>Back to route discovery</span>
      </button>

      <div className="itinerary-brand">
        <span className="itinerary-brand__text">
          <span className="itinerary-brand__namma">NAMMA</span>
          <span className="itinerary-brand__prayana"> PRAYANA</span>
          <small>Your Karnataka, your way</small>
        </span>
      </div>

      <span className="itinerary-topbar__tag">
        <Sparkles size={14} />
        Your travel story
      </span>
    </header>

    <section className="itinerary-hero">
      <div className="itinerary-hero__content">
        <p className="itinerary-eyebrow">
          <span /> YOUR KARNATAKA JOURNEY <span />
        </p>

        <h1>
          Every stop has
          <br />
          <em>a story to tell.</em>
        </h1>

        <p className="itinerary-hero__intro">
          A thoughtful travel plan shaped around your places, pace, budget,
          and the little moments that make a journey memorable.
        </p>

        <div className="itinerary-hero__chips">
          <span>
            <MapPin size={15} /> {destinations.length} destination
            {destinations.length === 1 ? "" : "s"}
          </span>
          <span>
            <CalendarDays size={15} /> {durationDays} day
            {durationDays === 1 ? "" : "s"}
          </span>
          <span>
            <Users size={15} /> {travellerCount} traveller
            {travellerCount === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      <div className="itinerary-hero__sun" aria-hidden="true" />
    </section>

    <div className="itinerary-main">
      <section className="itinerary-trip-summary">
        <div className="itinerary-trip-summary__place">
          <span className="itinerary-trip-summary__icon">
            <Compass size={20} />
          </span>
          <div>
            <span className="itinerary-label">YOUR ROUTE</span>
            <strong>
              {destinations.map(cityLabel).join("  →  ") ||
                "Choose your destinations"}
            </strong>
          </div>
        </div>

        <div className="itinerary-trip-summary__divider" />

        <div className="itinerary-trip-summary__item">
          <CalendarDays size={19} />
          <div>
            <span className="itinerary-label">TRAVEL DATES</span>
            <strong>
              {formatDate(startDate)} – {formatDate(endDate)}
            </strong>
          </div>
        </div>

        <div className="itinerary-trip-summary__divider" />

        <div className="itinerary-trip-summary__item">
          <Wallet size={19} />
          <div>
            <span className="itinerary-label">TOTAL GROUP BUDGET</span>
            <strong>
              {totalBudget ? formatCurrency(totalBudget) : "Not specified"}
            </strong>
          </div>
        </div>

        <button
          type="button"
          className="itinerary-edit-link"
          onClick={onBack}
        >
          Edit <ArrowRight size={15} />
        </button>
      </section>

      {/* Preferences and generation actions */}
      <section className="itinerary-adjust-section">
        <div className="itinerary-adjust-section__header">
          <div className="itinerary-adjust-section__intro">
            <span className="itinerary-adjust-section__symbol">
              <Heart size={22} />
            </span>

            <div>
              <p className="itinerary-eyebrow itinerary-eyebrow--left">
                TRAVEL THAT FITS YOUR GROUP
              </p>
              <h2>Make it feel right for everyone.</h2>
              <p>
                Choose your travel preferences before generating your
                personalised Karnataka itinerary.
              </p>
            </div>
          </div>

          <div className="itinerary-adjust-actions">
            <button
              type="button"
              className="itinerary-expand-button"
              onClick={() =>
                setShowTravellerNeeds((current) => !current)
              }
              aria-expanded={showTravellerNeeds}
            >
              {showTravellerNeeds
                ? "Close preferences"
                : "Apply My Preferences"}
              <ChevronDown
                size={17}
                className={showTravellerNeeds ? "is-rotated" : ""}
              />
            </button>

            <button
              type="button"
              className="itinerary-primary-button itinerary-generate-button"
              onClick={async () => {
                const request = [
                  `Revise the itinerary according to this travel pace: ${adjustment}.`,
                  travellerNeeds.length
                    ? `Traveller considerations: ${travellerNeeds.join(", ")}.`
                    : "",
                  specialNotes.trim()
                    ? `Additional requests: ${specialNotes.trim()}.`
                    : "",
                  "Preserve the selected destinations, dates, budget, and selected attractions wherever feasible. Use supplied database and weather records. Do not invent information.",
                ]
                  .filter(Boolean)
                  .join(" ");

                const success = await generatePreview(request);

                setAdjustmentMessage(
                  success
                    ? "Your personalised itinerary has been generated."
                    : "Itinerary generation failed. Check the error below and try again."
                );
              }}
              disabled={loading}
            >
              <Sparkles
                size={17}
                className={loading ? "itinerary-spin" : ""}
              />
              {loading ? "Generating Your Itinerary..." : "Get Your Itinerary"}
              {!loading && <ArrowRight size={16} />}
            </button>
          </div>
        </div>

        {showTravellerNeeds && (
          <div className="itinerary-adjust-form">
            <label className="itinerary-form-label">
              What kind of pace works best?
            </label>

            <div className="itinerary-choice-grid">
              {[
                ["balanced", "Balanced", "A mix of exploring and relaxing"],
                ["less-walking", "Less walking", "Shorter walks and more breaks"],
                ["rain-friendly", "Rain-friendly", "Prefer indoor alternatives if needed"],
                ["easy-pace", "Easy pace", "Fewer stops and more rest time"],
              ].map(([value, title, description]) => (
                <button
                  type="button"
                  key={value}
                  className={`itinerary-choice ${
                    adjustment === value ? "is-selected" : ""
                  }`}
                  onClick={() => setAdjustment(value)}
                >
                  <span className="itinerary-choice__check">
                    {adjustment === value && <Check size={13} />}
                  </span>
                  <strong>{title}</strong>
                  <small>{description}</small>
                </button>
              ))}
            </div>

            <label className="itinerary-form-label">
              Anything the plan should consider?
            </label>

            <div className="itinerary-needs-options">
              {[
                "Senior citizen travelling",
                "Child travelling",
                "Pregnant traveller",
                "Mobility or accessibility needs",
                "Avoid strenuous treks",
                "Prefer cooler / less exposed activities",
              ].map((need) => (
                <button
                  type="button"
                  key={need}
                  className={`itinerary-need-chip ${
                    travellerNeeds.includes(need) ? "is-selected" : ""
                  }`}
                  onClick={() => toggleNeed(need)}
                >
                  {travellerNeeds.includes(need) && <Check size={13} />}
                  {need}
                </button>
              ))}
            </div>

            <label
              className="itinerary-form-label"
              htmlFor="itinerary-special-notes"
            >
              Other requests <span>(optional)</span>
            </label>

            <textarea
              id="itinerary-special-notes"
              value={specialNotes}
              onChange={(event) => setSpecialNotes(event.target.value)}
              placeholder="For example: avoid steep climbs, include a longer lunch break, or keep evenings free…"
              rows={3}
            />

            {adjustmentMessage && (
              <p className="itinerary-adjust-message">
                {adjustmentMessage}
              </p>
            )}

            <p className="itinerary-disclaimer">
              These are travel preferences, not medical assessments.
              Confirm accessibility and health-related requirements
              with the relevant providers.
            </p>
          </div>
        )}
      </section>

      {/* Weather explorer */}
      <section className="itinerary-weather-section">
        <div className="itinerary-section-heading">
          <div>
            <p className="itinerary-eyebrow itinerary-eyebrow--left">
              PLAN WITH THE SKY
            </p>
            <h2>Weather explorer</h2>
            <p>Check the forecast for each city before you set out.</p>
          </div>

          <button
            type="button"
            className="itinerary-icon-button"
            onClick={loadWeather}
            disabled={weatherLoading}
            aria-label="Refresh weather"
          >
            <RefreshCw
              size={17}
              className={weatherLoading ? "itinerary-spin" : ""}
            />
          </button>
        </div>

        <div
          className="itinerary-weather-tabs"
          role="tablist"
          aria-label="Choose a city"
        >
          {destinations.map((city) => (
            <button
              key={city}
              type="button"
              role="tab"
              aria-selected={activeWeatherCity === city}
              className={activeWeatherCity === city ? "is-active" : ""}
              onClick={() => setActiveWeatherCity(city)}
            >
              <MapPin size={14} /> {cityLabel(city)}
            </button>
          ))}
        </div>

        {weatherLoading && !weather ? (
          <div className="itinerary-inline-state">
            <RefreshCw size={17} className="itinerary-spin" />
            Fetching weather details…
          </div>
        ) : weather?._error ? (
          <div className="itinerary-inline-state itinerary-inline-state--error">
            Weather is unavailable for {cityLabel(activeWeatherCity)} right now.
          </div>
        ) : weather ? (
          <div className="itinerary-weather-card">
            <div className="itinerary-weather-card__main">
              <span className="itinerary-weather-card__icon">
                <WeatherIcon size={30} />
              </span>
              <div>
                <span className="itinerary-label">
                  {cityLabel(activeWeatherCity)} · TRIP FORECAST
                </span>
                <strong className="itinerary-weather-card__condition">
                  {weatherDescription || "Forecast received"}
                </strong>
                <p>
                  {weather?.advice ??
                    "Use the forecast to plan outdoor activities."}
                </p>
              </div>
            </div>

            <div className="itinerary-weather-card__stats">
              <div>
                <span>Temperature</span>
                <strong>
                  {weather?.temperature ??
                    weather?.temperature_c ??
                    weather?.temp_c ??
                    "—"}
                  {weather?.temperature != null ||
                  weather?.temperature_c != null ||
                  weather?.temp_c != null
                    ? "°C"
                    : ""}
                </strong>
              </div>
              <div>
                <span>Rain chance</span>
                <strong>
                  {weather?.rain_probability ??
                    weather?.rain_chance ??
                    weather?.precipitation_probability ??
                    "—"}
                  {weather?.rain_probability != null ||
                  weather?.rain_chance != null ||
                  weather?.precipitation_probability != null
                    ? "%"
                    : ""}
                </strong>
              </div>
              <div>
                <span>Forecast date</span>
                <strong>{formatDate(weather?.date ?? startDate)}</strong>
              </div>
            </div>

            {weather?.source && (
              <p className="itinerary-source">Source: {weather.source}</p>
            )}
          </div>
        ) : (
          <div className="itinerary-inline-state">
            Weather information will appear when the forecast endpoint returns data.
          </div>
        )}

        {weatherError && (
          <p className="itinerary-muted-error">{weatherError}</p>
        )}

        <p className="itinerary-footnote">
          Forecast availability depends on the selected travel date and the
          weather service&apos;s forecast horizon.
        </p>
      </section>

      {/* Day-by-day itinerary */}
      <section className="itinerary-plan-section">
        <div className="itinerary-section-heading">
          <div>
            <p className="itinerary-eyebrow itinerary-eyebrow--left">
              YOUR DAYS, BEAUTIFULLY PLANNED
            </p>
            <h2>The journey, day by day</h2>
            <p>
              Explore the schedule and keep enough room for rest and discovery.
            </p>
          </div>

          {itinerary && (
            <button
              type="button"
              className="itinerary-secondary-button"
              onClick={() => generatePreview()}
              disabled={loading}
            >
              <RefreshCw
                size={16}
                className={loading ? "itinerary-spin" : ""}
              />
              {loading ? "Regenerating…" : "Regenerate Itinerary"}
            </button>
          )}
        </div>

        {pageError && (
          <div className="itinerary-error-panel">
            <AlertTriangle size={20} />
            <div>
              <strong>We couldn&apos;t load your plan yet.</strong>
              <p>{pageError}</p>
              <button
                type="button"
                onClick={() => generatePreview()}
                disabled={loading}
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {loading && !itinerary ? (
          <div className="itinerary-loading-panel">
            <span className="itinerary-loading-panel__icon">
              <Sparkles size={25} />
            </span>
            <strong>Creating your personalised journey…</strong>
            <p>
              Your itinerary is being generated. This may take a little while.
            </p>
          </div>
        ) : days.length > 0 ? (
          <div className="itinerary-day-layout">
            <nav className="itinerary-day-nav" aria-label="Itinerary days">
              {days.map((day, index) => (
                <button
                  type="button"
                  key={day?.day_number ?? day?.day ?? index}
                  className={activeDay === index ? "is-active" : ""}
                  onClick={() => setActiveDay(index)}
                >
                  <span className="itinerary-day-nav__number">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="itinerary-day-nav__text">
                    <strong>
                      {day?.title ?? day?.destination ?? `Day ${index + 1}`}
                    </strong>
                    <small>
                      {day?.date
                        ? formatDate(day.date)
                        : `Day ${index + 1} of ${days.length}`}
                    </small>
                  </span>
                  <ArrowRight size={15} />
                </button>
              ))}
            </nav>

            <div className="itinerary-day-detail">
              <div className="itinerary-day-detail__header">
                <div>
                  <span className="itinerary-label">
                    DAY {String(activeDay + 1).padStart(2, "0")}
                  </span>
                  <h3>
                    {selectedDay?.title ??
                      selectedDay?.destination ??
                      `Day ${activeDay + 1}`}
                  </h3>
                  <p>
                    {selectedDay?.date
                      ? formatDate(selectedDay.date)
                      : "Discover Karnataka at your own pace"}
                  </p>
                </div>
                <span className="itinerary-day-detail__stamp">
                  <Mountain size={19} /> Namma Nadu
                </span>
              </div>

              {selectedDay?.summary && (
                <p className="itinerary-day-summary">
                  {selectedDay.summary}
                </p>
              )}

              {selectedDayItems.length > 0 ? (
                <div className="itinerary-timeline">
                  {selectedDayItems.map((stop, index) => {
                    const cost = getStopCost(stop);

                    return (
                      <article
                        className="itinerary-stop"
                        key={
                          stop?.attraction_id ??
                          stop?.id ??
                          `${activeDay}-${index}`
                        }
                      >
                        <div className="itinerary-stop__rail">
                          <span className="itinerary-stop__dot">
                            {index + 1}
                          </span>
                          {index < selectedDayItems.length - 1 && (
                            <span className="itinerary-stop__line" />
                          )}
                        </div>

                        <div className="itinerary-stop__content">
                          <div className="itinerary-stop__meta">
                            {getStopTime(stop) && (
                              <span>
                                <Clock3 size={13} /> {getStopTime(stop)}
                              </span>
                            )}
                            {stop?.duration && (
                              <span>
                                <Clock3 size={13} /> {stop.duration}
                              </span>
                            )}
                            {stop?.category && (
                              <span className="itinerary-stop__category">
                                {stop.category}
                              </span>
                            )}
                          </div>

                          <h4>{getStopName(stop)}</h4>

                          {getStopDescription(stop) && (
                            <p>{getStopDescription(stop)}</p>
                          )}

                          {cost != null && (
                            <span className="itinerary-stop__cost">
                              Estimated {formatCurrency(cost)}
                            </span>
                          )}

                          {stop?.is_must_visit && (
                            <span className="itinerary-must-visit">
                              <Check size={12} /> Must visit
                            </span>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className="itinerary-empty-day">
                  <Compass size={24} />
                  <strong>No scheduled stops were returned for this day.</strong>
                  <p>
                    Refresh the itinerary or adjust your selected attractions.
                  </p>
                </div>
              )}

              {Array.isArray(selectedDay?.warnings) &&
                selectedDay.warnings.length > 0 && (
                  <div className="itinerary-day-warning">
                    <AlertTriangle size={17} />
                    <div>
                      {selectedDay.warnings.map((warning, index) => (
                        <p key={index}>{String(warning)}</p>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </div>
        ) : !pageError ? (
          <div className="itinerary-loading-panel itinerary-loading-panel--empty">
            <Compass size={27} />
            <strong>Your itinerary will appear here.</strong>
            <p>
              Choose your preferences and click Get Your Itinerary to generate
              your day-by-day plan.
            </p>
          </div>
        ) : null}

        {Array.isArray(itinerary?.warnings) &&
          itinerary.warnings.length > 0 && (
            <div className="itinerary-general-warnings">
              <strong>
                <AlertTriangle size={17} /> A few things to keep in mind
              </strong>
              {itinerary.warnings.map((warning, index) => (
                <p key={index}>
                  {typeof warning === "string"
                    ? warning
                    : warning?.message ?? JSON.stringify(warning)}
                </p>
              ))}
            </div>
          )}
      </section>

      {/* Food, stays and budget */}
      <section className="itinerary-discover-grid">
        <article className="itinerary-feature-card itinerary-feature-card--food">
          <div className="itinerary-feature-card__top">
            <span className="itinerary-feature-card__icon">
              <Utensils size={20} />
            </span>
            <span className="itinerary-feature-card__kicker">
              A TASTE OF KARNATAKA
            </span>
          </div>

          <h3>Local food worth the stop</h3>
          <p>
            Explore food spots from your selected cities, using the existing
            food database.
          </p>

          <button
            type="button"
            className="itinerary-text-button"
            onClick={() =>
              setOpenSection(openSection === "food" ? "" : "food")
            }
          >
            {openSection === "food" ? "Hide food picks" : "Explore food picks"}
            <ChevronDown
              size={16}
              className={openSection === "food" ? "is-rotated" : ""}
            />
          </button>

          {openSection === "food" && (
            <div className="itinerary-feature-expanded">
              <div className="itinerary-city-mini-tabs">
                {destinations.map((city) => (
                  <button
                    key={city}
                    type="button"
                    className={activeWeatherCity === city ? "is-active" : ""}
                    onClick={() => setActiveWeatherCity(city)}
                  >
                    {cityLabel(city)}
                  </button>
                ))}
              </div>

              {foodLoading ? (
                <p className="itinerary-feature-state">
                  <RefreshCw size={14} className="itinerary-spin" />
                  Loading food spots…
                </p>
              ) : foodItems.length ? (
                foodItems.slice(0, 5).map((food, index) => (
                  <div
                    className="itinerary-recommendation"
                    key={food.id ?? food.name ?? index}
                  >
                    <span className="itinerary-recommendation__icon">
                      <Coffee size={16} />
                    </span>
                    <div>
                      <strong>
                        {food.name ??
                          food.spot_name ??
                          food.restaurant_name ??
                          "Local food stop"}
                      </strong>
                      <p>
                        {food.dish ??
                          food.famous_dish ??
                          food.description ??
                          food.category ??
                          "Local speciality"}
                      </p>
                      {food.rating != null && <small>★ {food.rating}</small>}
                      {food.maps_link && (
                        <a
                          href={food.maps_link}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open map ↗
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <p className="itinerary-feature-state">
                  {foodError ||
                    `No food records were returned for ${cityLabel(
                      activeWeatherCity
                    )}.`}
                </p>
              )}
            </div>
          )}
        </article>

        <article className="itinerary-feature-card itinerary-feature-card--stay">
          <div className="itinerary-feature-card__top">
            <span className="itinerary-feature-card__icon">
              <Hotel size={20} />
            </span>
            <span className="itinerary-feature-card__kicker">
              REST WELL, TRAVEL WELL
            </span>
          </div>

          <h3>A stay that fits your journey</h3>
          <p>
            Ask the stays service for recommendations matching your group,
            dates, style, and budget.
          </p>

          <button
            type="button"
            className="itinerary-text-button"
            onClick={() =>
              setOpenSection(openSection === "stays" ? "" : "stays")
            }
          >
            {openSection === "stays" ? "Hide stays" : "Explore stays"}
            <ChevronDown
              size={16}
              className={openSection === "stays" ? "is-rotated" : ""}
            />
          </button>

          {openSection === "stays" && (
            <div className="itinerary-feature-expanded">
              {staysLoading ? (
                <p className="itinerary-feature-state">
                  <RefreshCw size={14} className="itinerary-spin" />
                  Finding suitable stays…
                </p>
              ) : stays.length ? (
                stays.slice(0, 5).map((stay, index) => (
                  <div
                    className="itinerary-recommendation"
                    key={stay.id ?? stay.name ?? index}
                  >
                    <span className="itinerary-recommendation__icon">
                      <Hotel size={16} />
                    </span>
                    <div>
                      <strong>
                        {stay.name ?? stay.hotel_name ?? "Recommended stay"}
                      </strong>
                      <p>
                        {stay.location ??
                          stay.city ??
                          stay.description ??
                          "Location details not provided"}
                      </p>
                      {(stay.price ??
                        stay.price_per_night ??
                        stay.estimated_price) != null && (
                        <small>
                          {formatCurrency(
                            stay.price ??
                              stay.price_per_night ??
                              stay.estimated_price
                          )}
                          {stay.price_per_night != null ? " / night" : ""}
                        </small>
                      )}
                      {stay.rating != null && <small> · ★ {stay.rating}</small>}
                      {(stay.booking_url ?? stay.booking_link ?? stay.url) && (
                        <a
                          href={
                            stay.booking_url ?? stay.booking_link ?? stay.url
                          }
                          target="_blank"
                          rel="noreferrer"
                        >
                          View stay ↗
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="itinerary-feature-state">
                  <p>
                    {staysError ||
                      "No stay recommendations have been returned yet."}
                  </p>
                  <button type="button" onClick={loadStays}>
                    Try again
                  </button>
                </div>
              )}

              <p className="itinerary-disclaimer">
                Prices and availability should be confirmed with the property
                or booking provider.
              </p>
            </div>
          )}
        </article>

        <article className="itinerary-feature-card itinerary-feature-card--budget">
          <div className="itinerary-feature-card__top">
            <span className="itinerary-feature-card__icon">
              <Wallet size={20} />
            </span>
            <span className="itinerary-feature-card__kicker">
              MONEY, WITHOUT THE MYSTERY
            </span>
          </div>

          <h3>Your budget at a glance</h3>
          <p>Keep the group budget visible while you plan each day.</p>

          <div className="itinerary-budget-summary">
            <div>
              <span>Group budget</span>
              <strong>
                {totalBudget ? formatCurrency(totalBudget) : "Not set"}
              </strong>
            </div>
            <div>
              <span>Per traveller</span>
              <strong>
                {totalBudget && travellerCount
                  ? formatCurrency(totalBudget / travellerCount)
                  : "—"}
              </strong>
            </div>
            <div>
              <span>Current estimate</span>
              <strong>
                {estimatedBudget ? formatCurrency(estimatedBudget) : "Not available"}
              </strong>
            </div>
          </div>

          {totalBudget > 0 && Number(estimatedBudget) > totalBudget && (
            <p className="itinerary-budget-warning">
              <AlertTriangle size={15} /> Current estimate is above your budget.
            </p>
          )}

          <p className="itinerary-disclaimer">
            Estimates are not confirmed quotes. Transport, meals, and stays may
            change the final cost.
          </p>
        </article>
      </section>

      <footer className="itinerary-footer">
        <span className="itinerary-footer__emblem">✳</span>
        <p>Made for the roads, stories, flavours, and soul of Karnataka.</p>
        <span className="itinerary-footer__kan">
          ನಮ್ಮ ನಾಡು · ನಮ್ಮ ಪ್ರಯಾಣ
        </span>
      </footer>
    </div>
  </main>
)
}