import { useEffect, useMemo, useState } from 'react';
import {
  CalendarDays,
  TrainFront,
  Clock3,
  ArrowRight,
  ExternalLink,
  LoaderCircle,
  Search,
  MapPin,
  RefreshCw,
  IndianRupee,
  Armchair,
} from 'lucide-react';
import './TrainSearchPanel.css';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const IRCTC_URL = 'https://www.irctc.co.in/nget/train-search';
const CLASSES = [
  ['SL', 'Sleeper (SL)'],
  ['3A', 'AC 3 Tier (3A)'],
  ['3E', 'AC 3 Economy (3E)'],
  ['2A', 'AC 2 Tier (2A)'],
  ['1A', 'AC First Class (1A)'],
  ['CC', 'AC Chair Car (CC)'],
  ['EC', 'Executive Chair Car (EC)'],
  ['2S', 'Second Sitting (2S)'],
  ['EA', 'Anubhuti (EA)'],
  ['FC', 'First Class (FC)'],
];
const QUOTAS = [
  ['GN', 'General'],
  ['TQ', 'Tatkal'],
  ['PT', 'Premium Tatkal'],
  ['LD', 'Ladies'],
  ['SS', 'Senior Citizen'],
];

function displayStation(station) {
  if (!station) return '';
  return `${station.name} (${station.code})`;
}

async function apiGet(path) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch {
    throw new Error('Cannot reach NammaPrayana backend. Make sure FastAPI is running on port 8000.');
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Backend returned an unreadable response.');
  }

  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : 'Railway request failed.';
    throw new Error(detail);
  }
  if (payload.success === false) {
    throw new Error(payload.error?.message || 'RailRadar could not complete this request.');
  }
  return payload;
}

function StationAutocomplete({ label, value, selectedStation, placeholder, onChange, onSelect }) {
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [suggestionError, setSuggestionError] = useState('');

  useEffect(() => {
    const query = value.trim();
    if (query.length < 2 || (selectedStation && value === displayStation(selectedStation))) {
      setSuggestions([]);
      setSuggestionError('');
      setLoadingSuggestions(false);
      return undefined;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoadingSuggestions(true);
      setSuggestionError('');
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/trains/stations?q=${encodeURIComponent(query)}&limit=10`,
          { signal: controller.signal },
        );
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Station search failed.');
        }
        const rows = Array.isArray(payload?.data) ? payload.data : [];
        setSuggestions(rows.filter((item) => item?.code && item?.name));
      } catch (err) {
        if (err.name !== 'AbortError') {
          setSuggestions([]);
          setSuggestionError(err.message || 'Could not search stations.');
        }
      } finally {
        if (!controller.signal.aborted) setLoadingSuggestions(false);
      }
    }, 280);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [value, selectedStation]);

  return (
    <label className="rd-train-search__field rd-train-api__station-field">
      <span><MapPin size={14} /> {label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        aria-autocomplete="list"
        required
      />
      {loadingSuggestions && <LoaderCircle className="rd-train-api__input-spinner" size={15} />}
      {suggestions.length > 0 && (
        <div className="rd-train-api__suggestions" role="listbox" aria-label={`${label} suggestions`}>
          {suggestions.map((station) => (
            <button
              type="button"
              className="rd-train-api__suggestion"
              key={station.code}
              onClick={() => {
                onSelect(station);
                setSuggestions([]);
                setSuggestionError('');
              }}
              role="option"
              aria-selected={selectedStation?.code === station.code}
            >
              <span className="rd-train-api__station-code">{station.code}</span>
              <span className="rd-train-api__station-name">
                <strong>{station.name}</strong>
                {station.city && <small>{station.city}</small>}
              </span>
            </button>
          ))}
        </div>
      )}
      {suggestionError && !loadingSuggestions && (
        <small className="rd-train-api__field-error">{suggestionError}</small>
      )}
      {value.trim().length >= 2 && !loadingSuggestions && !suggestionError && suggestions.length === 0 && !selectedStation && (
        <small className="rd-train-api__hint">No suggestions shown. Try the full station name or code.</small>
      )}
    </label>
  );
}

function formatDuration(minutes) {
  if (typeof minutes !== 'number' || !Number.isFinite(minutes) || minutes < 0) return 'Not provided';
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = Math.round(minutes % 60);
  if (!hours) return `${remainingMinutes} min`;
  if (!remainingMinutes) return `${hours} hr`;
  return `${hours} hr ${remainingMinutes} min`;
}

function formatMoney(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Not provided';
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value)}`;
}

function TrainResult({ item, onCheck, checking, classCode, quotaCode }) {
  const train = item?.train || {};
  const from = item?.from || {};
  const to = item?.to || {};
  return (
    <article className="rd-train-api__train-card">
      <div className="rd-train-api__train-topline">
        <div className="rd-train-api__train-title">
          <span className="rd-train-api__train-number">{train.number || 'Train number unavailable'}</span>
          <h4>{train.name || 'Train name not provided'}</h4>
          {train.type && <span className="rd-train-api__train-type">{train.type}</span>}
        </div>
        
      </div>
      <div className="rd-train-api__route-line">
        <div><strong>{from.departure || '—'}</strong><small>Departure</small></div>
        <div className="rd-train-api__route-duration"><span />{formatDuration(item?.duration)}<span /></div>
        <div><strong>{to.arrival || '—'}</strong><small>Arrival</small></div>
      </div>
      <div className="rd-train-api__meta-row">
        {typeof item?.distance === 'number' && <span>{item.distance} km</span>}
        {typeof item?.totalHaltsBetween === 'number' && <span>{item.totalHaltsBetween} halts</span>}
        {Array.isArray(train.runDays) && train.runDays.length > 0 && <span>Runs: {train.runDays.map((day) => String(day).toUpperCase()).join(', ')}</span>}
        <span>Class/quota check: {classCode} · {quotaCode}</span>
      </div>
    </article>
  );
}

function AvailabilityAndFare({ details, journeyDate }) {
  const seatData = details.seats;
  const fareData = details.fare;
  const calendar = Array.isArray(seatData?.calendar) ? seatData.calendar : [];
  const journeyDay = calendar.find((item) => item.date === journeyDate);
  const shownCalendar = journeyDay ? [journeyDay] : calendar.slice(0, 5);
  const breakdown = fareData?.breakdown;
  const fareLabels = [
    ['baseFare', 'Base fare'],
    ['reservationCharge', 'Reservation charge'],
    ['superfastCharge', 'Superfast charge'],
    ['otherCharge', 'Other charges'],
    ['tatkalFare', 'Tatkal charge'],
    ['goodsServiceTax', 'GST'],
    ['cateringCharge', 'Catering'],
    ['dynamicFare', 'Dynamic fare'],
    ['totalFare', 'Total fare'],
  ];

  return (
    <section className="rd-train-api__details" aria-live="polite">
      <h4><TrainFront size={17} /> Booking information</h4>
      <div className="rd-train-api__detail-grid">
        <div className="rd-train-api__detail-panel">
          <h5><Armchair size={15} /> Seat availability</h5>
          {details.seatError ? (
            <p className="rd-train-api__field-error">{details.seatError}</p>
          ) : seatData ? (
            <>
              <p className="rd-train-api__provider-caption">
                {seatData.trainName || 'Train'} · {seatData.classCode || 'Class not provided'} · {seatData.quotaCode || 'Quota not provided'}
              </p>
              {shownCalendar.length > 0 ? (
                <div className="rd-train-api__availability-list">
                  {shownCalendar.map((entry) => (
                    <div className="rd-train-api__availability-row" key={`${entry.date}-${entry.status}`}>
                      <span>{entry.date || 'Date not provided'}</span>
                      <strong>{entry.status || entry.statusCode || 'Status not provided'}</strong>
                      {typeof entry.availableSeats === 'number' && <small>{entry.availableSeats} seats</small>}
                    </div>
                  ))}
                </div>
              ) : (
                <p>RailRadar returned no availability calendar entries.</p>
              )}
              {!journeyDay && calendar.length > 0 && (
                <small className="rd-train-api__hint">The provider did not include {journeyDate} in this response. Dates above are shown exactly as returned.</small>
              )}
            </>
          ) : <p>Seat availability was not returned.</p>}
        </div>
        <div className="rd-train-api__detail-panel">
          <h5><IndianRupee size={15} /> Fare breakdown</h5>
          {details.fareError ? (
            <p className="rd-train-api__field-error">{details.fareError}</p>
          ) : fareData ? (
            <>
              <p className="rd-train-api__provider-caption">
                {fareData.trainName || 'Train'} · {fareData.distance != null ? `${fareData.distance} km` : 'Distance not provided'}
              </p>
              {breakdown && typeof breakdown === 'object' ? (
                <div className="rd-train-api__fare-list">
                  {fareLabels.filter(([key]) => breakdown[key] != null).map(([key, label]) => (
                    <div className={key === 'totalFare' ? 'rd-train-api__fare-total' : ''} key={key}>
                      <span>{label}</span><strong>{formatMoney(breakdown[key])}</strong>
                    </div>
                  ))}
                </div>
              ) : <p>RailRadar did not provide a fare breakdown for this request.</p>}
            </>
          ) : <p>Fare details were not returned.</p>}
        </div>
      </div>
      <p className="rd-train-api__source-note">Availability and fare are from RailRadar's API response and may change before booking. Confirm final details on IRCTC.</p>
    </section>
  );
}

export default function TrainSearchPanel() {
  const [sourceText, setSourceText] = useState('');
  const [destinationText, setDestinationText] = useState('');
  const [sourceStation, setSourceStation] = useState(null);
  const [destinationStation, setDestinationStation] = useState(null);
  const [journeyDate, setJourneyDate] = useState('');
  const [classCode, setClassCode] = useState('3A');
  const [quotaCode, setQuotaCode] = useState('GN');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [trains, setTrains] = useState(null);
  const [bookingDetails, setBookingDetails] = useState(null);
  const [checkingTrain, setCheckingTrain] = useState('');

  const minDate = useMemo(() => {
    const today = new Date();
    return [today.getFullYear(), String(today.getMonth() + 1).padStart(2, '0'), String(today.getDate()).padStart(2, '0')].join('-');
  }, []);

  async function handleSearch(event) {
    event.preventDefault();
    setError('');
    setTrains(null);
    setBookingDetails(null);

    if (!sourceStation || sourceText !== displayStation(sourceStation)) {
      setError('Choose the source station from the autocomplete suggestions.');
      return;
    }
    if (!destinationStation || destinationText !== displayStation(destinationStation)) {
      setError('Choose the destination station from the autocomplete suggestions.');
      return;
    }
    if (sourceStation.code === destinationStation.code) {
      setError('Source and destination stations must be different.');
      return;
    }
    if (!journeyDate || journeyDate < minDate) {
      setError('Choose today or a future journey date.');
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams({ from: sourceStation.code, to: destinationStation.code, date: journeyDate });
      const payload = await apiGet(`/api/trains/between?${params.toString()}`);
      const data = payload?.data;
      if (!data || !Array.isArray(data.trains)) {
        throw new Error('RailRadar returned an unexpected train-search response.');
      }
      setTrains(data);
    } catch (err) {
      setError(err.message || 'Train search failed. Please retry.');
    } finally {
      setLoading(false);
    }
  }

  async function handleBookingCheck(trainNumber) {
    const trainNumberKey = String(trainNumber);
    setCheckingTrain(trainNumberKey);
    setBookingDetails({ trainNumber: trainNumberKey, seats: null, fare: null, seatError: '', fareError: '', loading: true });
    const common = new URLSearchParams({
      source: sourceStation.code,
      destination: destinationStation.code,
      journeyDate,
      classCode,
      quotaCode,
    });
    const [seatResult, fareResult] = await Promise.allSettled([
      apiGet(`/api/trains/${encodeURIComponent(trainNumber)}/seats?${common.toString()}`),
      apiGet(`/api/trains/${encodeURIComponent(trainNumber)}/fare?${common.toString()}`),
    ]);

    setBookingDetails({
      trainNumber: trainNumberKey,
      seats: seatResult.status === 'fulfilled' ? seatResult.value?.data || null : null,
      fare: fareResult.status === 'fulfilled' ? fareResult.value?.data || null : null,
      seatError: seatResult.status === 'rejected' ? seatResult.reason.message : '',
      fareError: fareResult.status === 'rejected' ? fareResult.reason.message : '',
      loading: false,
    });
    setCheckingTrain('');
  }

  return (
    <section className="rd-train-search" aria-labelledby="rd-train-title">
      <div className="rd-train-search__heading">
        <span className="rd-train-search__eyebrow">
          <TrainFront size={16} /> RAIL JOURNEY
        </span>
        <h3 id="rd-train-title">Find Your Train</h3>
        <p>Search real train schedules, then check availability and fares from RailRadar.</p>
      </div>

      <form className="rd-train-search__form rd-train-api__form" onSubmit={handleSearch}>
        <StationAutocomplete
          label="From station"
          value={sourceText}
          selectedStation={sourceStation}
          placeholder="Search station name or code"
          onChange={(value) => { setSourceText(value); setSourceStation(null); }}
          onSelect={(station) => { setSourceStation(station); setSourceText(displayStation(station)); }}
        />
        <StationAutocomplete
          label="To station"
          value={destinationText}
          selectedStation={destinationStation}
          placeholder="Search station name or code"
          onChange={(value) => { setDestinationText(value); setDestinationStation(null); }}
          onSelect={(station) => { setDestinationStation(station); setDestinationText(displayStation(station)); }}
        />
        <label className="rd-train-search__field">
          <span><CalendarDays size={15} /> Journey date</span>
          <input type="date" value={journeyDate} min={minDate} onChange={(event) => setJourneyDate(event.target.value)} required />
        </label>
        <label className="rd-train-search__field">
          <span>Travel class</span>
          <select value={classCode} onChange={(event) => setClassCode(event.target.value)}>
            {CLASSES.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select>
        </label>
        <label className="rd-train-search__field">
          <span>Quota</span>
          <select value={quotaCode} onChange={(event) => setQuotaCode(event.target.value)}>
            {QUOTAS.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select>
        </label>
        <button className="rd-train-search__submit" type="submit" disabled={loading}>
          {loading ? <LoaderCircle className="rd-train-api__spin" size={17} /> : <Search size={17} />}
          {loading ? 'Searching RailRadar…' : 'Search Trains'}
          {!loading && <ArrowRight size={16} />}
        </button>
      </form>

      {error && <p className="rd-train-search__error" role="alert">{error}</p>}

      {trains && (
        <section className="rd-train-api__results" aria-live="polite">
          <div className="rd-train-api__results-heading">
            <div>
              <span className="rd-train-search__eyebrow"><TrainFront size={15} /> RAILRADAR RESULTS</span>
              <h4>{trains.from?.name || sourceStation?.name} <ArrowRight size={17} /> {trains.to?.name || destinationStation?.name}</h4>
              <p>{trains.count ?? trains.trains.length} train result(s) · {journeyDate}</p>
            </div>
            <button type="button" className="rd-train-api__text-button" onClick={() => { setTrains(null); setBookingDetails(null); }}>
              <RefreshCw size={14} /> Clear results
            </button>
          </div>
          {trains.trains.length === 0 ? (
            <div className="rd-train-api__empty"><TrainFront size={23} /><strong>No trains returned for this search.</strong><p>RailRadar returned no matching trains for these stations and date.</p></div>
          ) : (
            <div className="rd-train-api__train-list">
              {trains.trains.map((item, index) => {
                const number = item?.train?.number || `unknown-${index}`;
                return (
                  <TrainResult
                    key={`${number}-${index}`}
                    item={item}
                    onCheck={handleBookingCheck}
                    checking={checkingTrain === String(number)}
                    classCode={classCode}
                    quotaCode={quotaCode}
                  />
                );
              })}
            </div>
          )}
        </section>
      )}

      {bookingDetails?.loading && (
        <div className="rd-train-api__loading-panel" role="status"><LoaderCircle size={19} className="rd-train-api__spin" /> Fetching availability and fare from RailRadar…</div>
      )}
      {bookingDetails && !bookingDetails.loading && <AvailabilityAndFare details={bookingDetails} journeyDate={journeyDate} />}

      <div className="rd-train-search__notice rd-train-api__notice">
        <Clock3 size={19} />
        <div>
          <strong>Verify before booking.</strong>
          <p>Schedules, availability and fares are provider results and can change. Complete the booking through the official railway channel.</p>
          <a href={IRCTC_URL} target="_blank" rel="noreferrer">Continue to official IRCTC search <ExternalLink size={14} /></a>
        </div>
      </div>
      <p className="rd-train-search__footnote"><Clock3 size={14} /> Powered by RailRadar API through the NammaPrayana backend. API keys are never sent to the browser.</p>
    </section>
  );
}