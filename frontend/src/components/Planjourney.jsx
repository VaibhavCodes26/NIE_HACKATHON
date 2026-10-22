import { Fragment, useMemo, useState } from 'react';
import { commonsImg } from '../data/destinations';
import {
    ArrowDown, ArrowLeft, ArrowUp, CalendarDays, Check, CloudSun, ExternalLink,
    Hotel, MapPin, Plus, Sparkles, Trash2, Users, Wallet, AlertTriangle, LoaderCircle,
    Bus, TrainFront, CarFront, Footprints, MapPinned
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

const DESTINATIONS = [
    { id: 'badami', name: 'Badami', region: 'North Karnataka' },
    { id: 'hampi', name: 'Hampi', region: 'Vijayanagara' },
    { id: 'mysuru', name: 'Mysuru', region: 'Mysuru region' },
    { id: 'bengaluru', name: 'Bengaluru', region: 'South Karnataka' },
    { id: 'coorg', name: 'Coorg (Madikeri)', region: 'Western Ghats' },
    { id: 'chikkamagaluru', name: 'Chikkamagaluru', region: 'Western Ghats' },
    { id: 'mangaluru', name: 'Mangaluru', region: 'Coastal Karnataka' },
    { id: 'udupi', name: 'Udupi', region: 'Coastal Karnataka' },
    { id: 'gokarna', name: 'Gokarna', region: 'Coastal Karnataka' },
    { id: 'dandeli', name: 'Dandeli', region: 'Western Karnataka' },
    { id: 'shivamogga', name: 'Shivamogga', region: 'Malnad' },
    { id: 'belur-halebidu', name: 'Belur & Halebidu', region: 'Hassan region' },
    { id: 'vijayapura', name: 'Vijayapura', region: 'North Karnataka' },
    { id: 'bidar', name: 'Bidar', region: 'North Karnataka' },
    { id: 'chitradurga', name: 'Chitradurga', region: 'Central Karnataka' },
    { id: 'belagavi', name: 'Belagavi', region: 'Northwest Karnataka' },
    {id: "hubballi" ,name: "Hubballi", region: "North Karnataka"},
    {id:"hassan",name:"Hassan",region:"South western Karnataka"},
];

const INTERESTS = [
    'Heritage & culture', 'Tourist attractions', 'Local food', 'Nature & hills',
    'Beaches', 'Adventure', 'Hidden gems', 'Festivals & traditions',
];

const STYLES = [
    { id: 'budget', name: 'Budget-friendly', note: 'Value stays and practical choices' },
    { id: 'comfortable', name: 'Comfortable', note: 'Balanced comfort and spending' },
    { id: 'premium', name: 'Premium', note: 'Higher-comfort stays and experiences' },
    { id: 'ultra-premium', name: 'Ultra-premium', note: 'Luxury-oriented trip preferences' },
];



function dateString(date) {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
}

function formatINR(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency', currency: 'INR', maximumFractionDigits: 0,
    }).format(amount);
}

function formatDate(value) {
    return new Date(`${value}T12:00:00`).toLocaleDateString('en-IN', {
        weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
    });
}

export default function PlanJourney({
    onBack,
    onPreview,
    previewOnly = false,
    initialResult = null,
    landingSection = false,
    onDiveIntoJourney = null,
}) {
    const today = useMemo(() => dateString(new Date()), []);
    const defaultEnd = useMemo(() => {
        const date = new Date();
        date.setDate(date.getDate() + 2);
        return dateString(date);
    }, []);
// initial values kept in the page
    const [selectedDestinations, setSelectedDestinations] = useState([]);
    const [destinationToAdd, setDestinationToAdd] = useState('mysuru');
    const [startDate, setStartDate] = useState(today);
    const [endDate, setEndDate] = useState(defaultEnd);
    const [travellerCount, setTravellerCount] = useState(3);
    const [travelStyle, setTravelStyle] = useState('premium');
    const [totalBudget, setTotalBudget] = useState(10000);
    const [interests, setInterests] = useState(['Heritage & culture', 'Local food']);
    const [result, setResult] = useState(initialResult);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [weatherByDay, setWeatherByDay] = useState({});
    const [weatherLoading, setWeatherLoading] = useState({});

    const durationDays = startDate && endDate
        ? Math.floor((new Date(`${endDate}T12:00:00`) - new Date(`${startDate}T12:00:00`)) / 86400000) + 1
        : 0;
    const chosenDestinations = selectedDestinations
        .map((id) => DESTINATIONS.find((item) => item.id === id))
        .filter(Boolean);
    const availableToAdd = DESTINATIONS.filter((item) => !selectedDestinations.includes(item.id));

    const addDestination = () => {
        if (!destinationToAdd || selectedDestinations.includes(destinationToAdd) || selectedDestinations.length >= 8) return;
        setSelectedDestinations((current) => [...current, destinationToAdd]);
        setDestinationToAdd(DESTINATIONS.find((item) => !selectedDestinations.includes(item.id) && item.id !== destinationToAdd)?.id || '');
        setResult(null);
    };

    const removeDestination = (id) => {
        setSelectedDestinations((current) => current.filter((item) => item !== id));
        setResult(null);
    };

    const moveDestination = (index, direction) => {
        const nextIndex = index + direction;
        if (nextIndex < 0 || nextIndex >= selectedDestinations.length) return;
        setSelectedDestinations((current) => {
            const next = [...current];
            [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
            return next;
        });
        setResult(null);
    };

    const toggleInterest = (interest) => {
        setInterests((current) => current.includes(interest)
            ? current.filter((item) => item !== interest)
            : [...current, interest]);
        setResult(null);
    };

    const generatePlan = async (event) => {
        event.preventDefault();
        setError('');
        setResult(null);
        setWeatherByDay({});
        if (selectedDestinations.length === 0) {
            setError('Please add at least one destination to plan your journey.');
            return;
        }
        if (durationDays < 1) {
            setError('The end date must be on or after the start date.');
            return;
        }
        if (durationDays < selectedDestinations.length) {
            setError('Choose at least one calendar day per destination, or remove a destination to fit your dates.');
            return;
        }

        if (onDiveIntoJourney) {
            onDiveIntoJourney({
                destinations: selectedDestinations,
                startDate,
                endDate,
                travellerCount: Number(travellerCount),
                travelStyle,
                totalBudget: Number(totalBudget),
                interests,
            });
            return;
        }

        setLoading(true);
        
try {
    const savedSelection = sessionStorage.getItem('np_selected_itinerary');
    const itinerarySelection = savedSelection
        ? JSON.parse(savedSelection)
        : null;

    const response = await fetch(`${API_BASE}/api/itineraries/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            destinations: selectedDestinations,
            start_date: startDate,
            end_date: endDate,
            traveller_count: Number(travellerCount),
            travel_style: travelStyle,
            total_budget: Number(totalBudget),
            interests,
            selected_attraction_ids:
                itinerarySelection?.selected_attraction_ids ?? [],
        }),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = Array.isArray(payload.detail)
            ? payload.detail.map((item) => item.msg).join(', ')
            : payload.detail;

        throw new Error(
            detail || 'The planner could not build this draft.'
        );
    }

    setResult(payload);

    if (onPreview) onPreview(payload);
} catch (err) {
    setError(
        `Could not reach the NammaPrayana backend at ${API_BASE}. ` +
        `Start the FastAPI server and try again. ${err.message || ''}`
    );
} finally {
    setLoading(false);
}

       
    };

    const checkWeather = async (day) => {
        setWeatherLoading((current) => ({ ...current, [day.day_number]: true }));
        try {
            const destination = day.destination_id === 'badami' ? 'Badami & Aihole' : day.destination_name;
            const params = new URLSearchParams({ destination, date: day.date });
            const response = await fetch(`${API_BASE}/api/weather/forecast?${params.toString()}`);
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || 'Forecast unavailable for this date.');
            setWeatherByDay((current) => ({ ...current, [day.day_number]: { ...payload, error: '' } }));
        } catch (err) {
            setWeatherByDay((current) => ({ ...current, [day.day_number]: { error: err.message || 'Forecast unavailable.' } }));
        } finally {
            setWeatherLoading((current) => ({ ...current, [day.day_number]: false }));
        }
    };

    const Tag = landingSection ? 'section' : 'main';

    return (
        <Tag id={landingSection ? 'plan' : undefined} className={`journey-page multi-planner-page ${landingSection ? 'landing-plan-section' : ''}`}>

            <div className="journey-container">
                {!landingSection && onBack && (
                    <button className="journey-back" type="button" onClick={onBack}>
                        <ArrowLeft size={17} /> {previewOnly ? "Back to trip setup" : "Home page"}
                    </button>
                )}

                {!previewOnly && <>
                    <header className="multi-planner-heading">
                        <div className="journey-kicker"><Sparkles size={16} /> YOUR KARNATAKA STORY</div>
                        <h1>Plan a journey, <span>not just a destination.</span></h1>
                        <p>Choose the places you want to explore. NammaPrayana will arrange a curated day-by-day draft around your dates, group, interests and budget.</p>
                    </header>

                    <section className="karnataka-showcase" aria-label="Discover Karnataka's heritage and traditions">
                        <div className="karnataka-showcase-intro">
                            <span className="karnataka-showcase-eyebrow">ROOTED IN KARNATAKA</span>
                            <h2>Every place has a story.<br /><em>Every tradition has a soul.</em></h2>
                            <p>From temple-carved stone to the rhythm of folk performances and the flavours of a local kitchen.</p>
                        </div>
                        <div className="karnataka-showcase-grid">
                            <article className="karnataka-showcase-card ksc-hampi">
                                <img src={commonsImg('Hampi, Vittala Temple, chariot (9881832023).jpg', 900)} alt="The stone chariot at Hampi" loading="lazy" />
                                <span className="ksc-tag">WORLD HERITAGE</span><div><small>VIJAYANAGARA LEGACY</small><h3>Hampi</h3><p>Ancient kingdoms, boulder hills and monumental stonework.</p></div>
                            </article>
                            <article className="karnataka-showcase-card ksc-mysuru">
                                <img src={commonsImg('Mysore Palace, Mysuru.jpg', 900)} alt="Mysore Palace in Karnataka" loading="lazy" />
                                <span className="ksc-tag">ROYAL KARNATAKA</span><div><small>PALACE · DASARA</small><h3>Mysuru</h3><p>Royal architecture, festival lights and living traditions.</p></div>
                            </article>
                            <article className="karnataka-showcase-card ksc-badami">
                                <img src={commonsImg('Cave Temples at Badami.jpg', 900)} alt="The sandstone cave temples of Badami" loading="lazy" />
                                <span className="ksc-tag">CARVED IN STONE</span><div><small>CHALUKYA HERITAGE</small><h3>Badami</h3><p>Red sandstone cliffs shaped by centuries of artistry.</p></div>
                            </article>
                        </div>
                        <div className="karnataka-culture-ribbon" aria-label="Karnataka cultural highlights">
                            <span className="culture-ribbon-mark" aria-hidden="true">✳</span>
                            <div><small>FOLK PERFORMANCE</small><strong>Yakshagana</strong><span>Colour, rhythm & mythology</span></div>
                            <i aria-hidden="true"></i>
                            <div><small>FROM THE LOCAL KITCHEN</small><strong>Oota & Tindi</strong><span>Regional flavours worth travelling for</span></div>
                            <i aria-hidden="true"></i>
                            <div><small>CRAFT & COMMUNITY</small><strong>Living Traditions</strong><span>Stories passed from generation to generation</span></div>
                        </div>
                    </section>
                </>}

                {!previewOnly && <form className="multi-planner-form" onSubmit={generatePlan}>
                    <section className="multi-planner-card">
                        <div className="multi-planner-section-title">
                            <span className="multi-planner-icon"><MapPin size={20} /></span>
                            <div><h2>Your route</h2><p>Add destinations and arrange them in the order you want to visit.</p></div>
                        </div>

                        <div className="multi-destination-list">
                            {chosenDestinations.map((destination, index) => (
                                <div className="multi-destination-row" key={destination.id}>
                                    <span className="multi-destination-number">{index + 1}</span>
                                    <div className="multi-destination-copy">
                                        <strong>{destination.name}</strong>
                                        <small>{destination.region}</small>
                                    </div>
                                    <div className="multi-destination-actions">
                                        <button type="button" aria-label={`Move ${destination.name} up`} title="Move up" disabled={index === 0} onClick={() => moveDestination(index, -1)}><ArrowUp size={16} /></button>
                                        <button type="button" aria-label={`Move ${destination.name} down`} title="Move down" disabled={index === chosenDestinations.length - 1} onClick={() => moveDestination(index, 1)}><ArrowDown size={16} /></button>
                                        <button type="button" aria-label={`Remove ${destination.name}`} title="Remove destination" disabled={false} onClick={() => removeDestination(destination.id)}><Trash2 size={16} /></button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="multi-add-destination">
                            <label htmlFor="destination-to-add">Add another place</label>
                            <div className="multi-add-controls">
                                <select id="destination-to-add" value={destinationToAdd} onChange={(event) => setDestinationToAdd(event.target.value)} disabled={!availableToAdd.length || selectedDestinations.length >= 8}>
                                    {availableToAdd.length
                                        ? availableToAdd.map((destination) => <option key={destination.id} value={destination.id}>{destination.name} · {destination.region}</option>)
                                        : <option value="">All destinations added</option>}
                                </select>
                                <button className="multi-add-button" type="button" onClick={addDestination} disabled={!availableToAdd.length || selectedDestinations.length >= 8}><Plus size={17} /> Add</button>
                            </div>
                            <small>Choose 1–8 destinations. One-city trips are welcome. Use the arrows to change your route order; no departure city is required.</small>
                        </div>
                    </section>

                    <section className="multi-planner-card">
                        <div className="multi-planner-section-title">
                            <span className="multi-planner-icon"><CalendarDays size={20} /></span>
                            <div><h2>When are you travelling?</h2><p>Trip duration is calculated from your start and end dates, inclusive.</p></div>
                        </div>
                        <div className="multi-planner-fields">
                            <label className="multi-field"><span>Start date</span><input type="date" value={startDate} min={today} required onChange={(event) => { const nextStart = event.target.value; setStartDate(nextStart); if (endDate < nextStart) setEndDate(nextStart); setResult(null); }} /></label>
                            <label className="multi-field"><span>End date</span><input type="date" value={endDate} min={startDate || today} required onChange={(event) => { setEndDate(event.target.value); setResult(null); }} /></label>
                            <div className="multi-duration-summary"><CalendarDays size={19} /><div><strong>{durationDays > 0 ? `${durationDays} ${durationDays === 1 ? 'day' : 'days'}` : 'Choose dates'}</strong><small>Trip duration</small></div></div>
                        </div>
                    </section>

                    <section className="multi-planner-card">
                        <div className="multi-planner-section-title">
                            <span className="multi-planner-icon"><Users size={20} /></span>
                            <div><h2>Your travel group</h2><p>Budget means the total amount for everyone, for the entire trip.</p></div>
                        </div>
                        <div className="multi-planner-fields multi-group-fields">
                            <label className="multi-field"><span>Number of travellers</span><div className="multi-number-input"><button type="button" aria-label="Remove one traveller" disabled={travellerCount <= 1} onClick={() => setTravellerCount((value) => Math.max(1, value - 1))}>−</button><strong>{travellerCount}</strong><button type="button" aria-label="Add one traveller" disabled={travellerCount >= 30} onClick={() => setTravellerCount((value) => Math.min(30, value + 1))}>+</button></div></label>
                            <div className="multi-budget-summary"><span><Wallet size={17} /> Total group budget</span><strong>{formatINR(totalBudget)}</strong><small>About {formatINR(totalBudget / Math.max(1, travellerCount))} per traveller for the whole trip</small></div>
                        </div>
                        <label className="multi-budget-slider" htmlFor="group-budget"><span>Adjust your total group budget</span><input id="group-budget" type="range" min="1000" max="100000" step="1000" value={totalBudget} onChange={(event) => { setTotalBudget(Number(event.target.value)); setResult(null); }} /><div><small>₹1,000</small><small>₹1,00,000</small></div></label>
                    </section>

                    <section className="multi-planner-card">
                        <div className="multi-planner-section-title">
                            <span className="multi-planner-icon"><Hotel size={20} /></span>
                            <div><h2>Choose your travel style</h2><p>This guides the type of stay and experience suggestions; it does not guarantee prices.</p></div>
                        </div>
                        <div className="multi-style-grid">
                            {STYLES.map((style) => (
                                <button className={`multi-style-option ${travelStyle === style.id ? 'is-selected' : ''}`} key={style.id} type="button" aria-pressed={travelStyle === style.id} onClick={() => { setTravelStyle(style.id); setResult(null); }}>
                                    <span className="multi-style-check">{travelStyle === style.id && <Check size={14} />}</span><strong>{style.name}</strong><small>{style.note}</small>
                                </button>
                            ))}
                        </div>
                    </section>

                    <section className="multi-planner-card">
                        <div className="multi-planner-section-title">
                            <span className="multi-planner-icon"><Sparkles size={20} /></span>
                            <div><h2>What do you love exploring?</h2><p>Pick all the interests you want reflected in the draft.</p></div>
                        </div>
                        <div className="multi-interest-grid">
                            {INTERESTS.map((interest) => (
                                <label className={`multi-interest-chip ${interests.includes(interest) ? 'is-selected' : ''}`} key={interest}>
                                    <input type="checkbox" checked={interests.includes(interest)} onChange={() => toggleInterest(interest)} />
                                    <span>{interest}</span>{interests.includes(interest) && <Check size={15} />}
                                </label>
                            ))}
                        </div>
                    </section>

                    {error && <div className="multi-planner-error" role="alert"><AlertTriangle size={18} /><span>{error}</span></div>}

                    <button className="multi-generate-button" type="submit" disabled={loading}>
                        {loading ? <><LoaderCircle className="multi-spin" size={19} /> Building your draft…</> : <><Sparkles size={19} /> Dive Into Your Journey <span>→</span></>}
                    </button>
                    <p className="multi-form-footnote">Your route and preferences are sent to your local NammaPrayana backend. This creates a curated preview, not a booking.</p>
                </form>}


                {result && (
                    <section className={"multi-results " + (previewOnly ? "is-standalone-preview" : "")} aria-live="polite">
                        <section className="journey-intro-banner" aria-label="Discover Karnataka">
                            <span className="journey-intro-kicker">NAMMA PRAYANA · STORIES OF KARNATAKA</span>
                            <p>Where ancient kingdoms whisper through stone, traditions live in every celebration, and every journey reveals the soul of Karnataka.</p>
                        </section>

                        <header className="multi-results-header">
                            <div><span className="journey-kicker"><Check size={15} /> YOUR FIRST DRAFT</span><h2>{result.title}</h2><p>{formatDate(result.start_date)} — {formatDate(result.end_date)} · {result.duration_days} days · {result.traveller_count} travellers</p></div>
                            <div className="multi-results-budget"><small>Total group budget</small><strong>{formatINR(result.total_budget)}</strong><small>{formatINR(result.budget_per_traveller)} per traveller</small></div>
                        </header>

                        <div className="multi-result-route"><strong>Your route</strong>{result.destinations.map((destination, index) => <span key={destination.id}>{index > 0 && <b>→</b>} {destination.name}</span>)}</div>

                        <section className="journey-transport-panel" aria-labelledby="journey-transport-title">
                            <div className="journey-transport-heading">
                                <div>
                                    <span className="journey-transport-eyebrow">YOUR ROUTE, YOUR WAY</span>
                                    <h3 id="journey-transport-title">HOW YOU CAN GO?</h3>
                                    <p>Choose a route to explore transport options across Karnataka.</p>
                                </div>
                            </div>
                            <div className="journey-route-fields">
                                <div className="journey-route-field">
                                    <span>STARTING POINT</span>
                                    <strong><MapPin size={16} /> {result.destinations[0]?.name || 'Your starting point'}</strong>
                                </div>
                                <div className="journey-route-connector" aria-hidden="true">→</div>
                                <div className="journey-route-field">
                                    <span>TOURIST PLACE</span>
                                    <strong><MapPinned size={16} /> {result.destinations[result.destinations.length - 1]?.name || 'Your destination'}</strong>
                                </div>
                            </div>
                            <div className="journey-route-mode-label">EXPLORE TRANSPORT MODES</div>
                            <div className="journey-route-modes">
                                {[
                                    { label: 'TAXI', mode: 'driving', icon: <CarFront size={18} /> },
                                    { label: 'TRAIN', mode: 'transit', icon: <TrainFront size={18} /> },
                                    { label: 'METRO', mode: 'transit', icon: <TrainFront size={18} /> },
                                    { label: 'BUS', mode: 'transit', icon: <Bus size={18} /> }
                                ].map((option) => {
                                    const origin = result.destinations[0]?.name || '';
                                    const destination = result.destinations[result.destinations.length - 1]?.name || '';
                                    const url = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&travelmode=${option.mode}`;
                                    return <a className="journey-route-mode" href={url} target="_blank" rel="noreferrer" key={option.label}>
                                        {option.icon}<span>{option.label}</span><ExternalLink size={13} />
                                    </a>;
                                })}
                            </div>
                            <p className="journey-route-disclaimer">Opens route exploration in Google Maps. Actual services, schedules and fares depend on the selected route and provider.</p>
                        </section>

                        <div className="multi-day-list">
                            {result.days.map((day, dayIndex) => (
                                <Fragment key={day.day_number}>
                                    <article className="multi-day-card" key={day.day_number}>
                                        <div className="multi-day-heading"><span className="multi-day-number">DAY {day.day_number}</span><div><h3>{day.destination_name}</h3><p>{formatDate(day.date)}</p></div></div>

                                        <div className="multi-stop-list">{day.stops.map((stop, index) => <div className="multi-stop is-featured-attraction" key={`${day.day_number}-${stop.name}`}><span className="multi-stop-time">{stop.suggested_time}</span><span className="multi-stop-dot">{index + 1}</span><div><strong>{stop.name}<span className="featured-attraction-badge"><Sparkles size={11} /> ITINERARY PICK</span></strong><p>{stop.description}</p></div></div>)}</div>

                                        <div className="multi-day-tools"><button type="button" onClick={() => checkWeather(day)} disabled={Boolean(weatherLoading[day.day_number])}>{weatherLoading[day.day_number] ? <LoaderCircle className="multi-spin" size={15} /> : <CloudSun size={16} />} Check forecast</button></div>
                                        {weatherByDay[day.day_number] && <div className={`multi-weather-result ${weatherByDay[day.day_number].error ? 'has-error' : ''}`}>{weatherByDay[day.day_number].error ? weatherByDay[day.day_number].error : <><CloudSun size={18} /><span><strong>{weatherByDay[day.day_number].temperature_min_c}°–{weatherByDay[day.day_number].temperature_max_c}°C</strong><small>Rain chance: {weatherByDay[day.day_number].rain_probability_percent == null ? 'not provided' : `${weatherByDay[day.day_number].rain_probability_percent}%`} · {weatherByDay[day.day_number].travel_advice}</small><small>Forecast by {weatherByDay[day.day_number].source}; estimates can change.</small></span></>}</div>}
                                    </article>
                                </Fragment>
                            ))}
                        </div>

                        <div className="multi-warning-list">{result.warnings.map((warning) => <div key={warning.code} className={warning.severity === 'warning' ? 'is-warning' : ''}><AlertTriangle size={16} /><span>{warning.message}</span></div>)}</div>
                        <button className="multi-edit-button" type="button" onClick={() => { if (previewOnly) { onBack?.(); } else { setResult(null); window.scrollTo({ top: 0, behavior: 'smooth' }); } }}>← Edit trip preferences</button>
                    </section>
                )}
            </div>
        </Tag>
    );
}