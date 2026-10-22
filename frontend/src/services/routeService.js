// Service layer for route options.
//
// Today: derives ILLUSTRATIVE figures from straight-line distance between two points.
// Later: replace the body of `getRouteOptions` with a fetch to your FastAPI backend, e.g.
//
//   const res = await fetch(`/api/routes?from=${from.id}&to=${to.id}`);
//   return res.json();
//
// As long as the returned shape stays the same, no UI component needs to change.
//
// Shape: { distanceKm, isIllustrative, modes: { taxi, walking, train, metro, bus } }
// Each mode: { available, durationMin, distanceKm, fare, summary, steps[], notes[], warning?, extra }

const R = 6371;
const toRad = (d) => (d * Math.PI) / 180;

export function haversineKm(a, b) {
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function formatDuration(min) {
  const m = Math.round(min);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h} hr ${r} min` : `${h} hr`;
}

const inr = (n) => `₹${Math.round(n / 10) * 10}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

const METRO_CITIES = new Set(['blr']); // Namma Metro (Bengaluru) — prototype logic only
const hasMetro = (loc) => METRO_CITIES.has(loc.id) || loc.hint?.includes('Bengaluru');

function clock(base, addMin) {
  const t = base + addMin;
  const hh = Math.floor((t / 60) % 24);
  const mm = Math.round(t % 60);
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

export function buildMockRoutes(from, to) {
  const straight = haversineKm(from, to);
  const road = Math.max(1, straight * 1.28); // roads wind
  const rail = Math.max(1, straight * 1.18);

  const sameCity = straight < 12;
  const walkMin = (road / 4.8) * 60;

  const taxiMin = (road / 52) * 60 + 8;
  const taxiFare = 60 + road * 15;

  const busMin = (road / 40) * 60 + 20;
  const busFare = Math.max(20, road * 1.9);

  const trainMin = (rail / 55) * 60 + 25;
  const trainFare = Math.max(40, rail * 1.1);

  // Metro only plausible when both ends are within Bengaluru urban area (prototype rule)
  const metroPossible = hasMetro(from) && hasMetro(to) && straight < 45;
  const metroMin = (straight / 32) * 60 + 12;
  const metroFare = Math.min(90, 10 + straight * 3.2);

  const walkWarning =
    road > 25
      ? 'This is far too long to walk. Please choose Taxi, Train or Bus for this journey.'
      : road > 8
      ? 'Long walking distance — carry water, plan rest stops and avoid midday heat.'
      : road > 4
      ? 'A longer walk. Wear comfortable footwear and check pavement conditions.'
      : null;

  const dep = 6 * 60 + 30; // illustrative first departure 06:30

  return {
    distanceKm: road,
    isIllustrative: true,
    modes: {
      taxi: {
        available: true,
        distanceKm: road,
        durationMin: taxiMin,
        fare: inr(taxiFare),
        fareNote: 'Illustrative estimate',
        summary: `A direct road journey from ${from.name} to ${to.name} with door-to-door comfort.`,
        steps: [
          `Book a cab from ${from.name}`,
          road > 60 ? 'Take the main highway corridor with a short tea/rest stop' : 'Follow the fastest city and state roads',
          `Arrive at ${to.name}`,
        ],
        notes: ['Fare shown is a placeholder estimate, not a live quote.', 'Tolls and waiting charges may apply.'],
        extra: [{ label: 'Pickup', value: 'On demand' }],
      },
      walking: {
        available: true,
        distanceKm: road,
        durationMin: walkMin,
        fare: 'Free',
        summary: sameCity
          ? `A walkable route within the area between ${from.name} and ${to.name}.`
          : `Walking between ${from.name} and ${to.name} is not practical for most travellers.`,
        steps: [`Start from ${from.name}`, 'Follow pedestrian-friendly roads where available', `Reach ${to.name}`],
        notes: ['Estimated at an average pace of about 4.8 km/h.'],
        warning: walkWarning,
        extra: [{ label: 'Pace', value: '≈ 4.8 km/h' }],
      },
      train: {
        available: straight > 15,
        distanceKm: rail,
        durationMin: trainMin,
        fare: inr(trainFare),
        fareNote: 'Illustrative, sleeper/2S range',
        summary: `Rail connection between ${from.name} and ${to.name}. Routing and train numbers will come from the live service.`,
        steps: [`Reach the nearest station in ${from.name}`, 'Board the connecting train (details to be confirmed)', `Alight near ${to.name}`],
        notes: ['Timings below are illustrative placeholders.', 'Check the official railway service for actual schedules.'],
        extra: [
          { label: 'Departure', value: clock(dep, 0) + ' (sample)' },
          { label: 'Arrival', value: clock(dep, trainMin) + ' (sample)' },
        ],
      },
      metro: {
        available: metroPossible,
        distanceKm: straight * 1.1,
        durationMin: metroMin,
        fare: inr(metroFare),
        fareNote: 'Illustrative estimate',
        summary: metroPossible
          ? `Urban metro link between ${from.name} and ${to.name}.`
          : `Metro service is not available between ${from.name} and ${to.name}.`,
        steps: metroPossible
          ? [`Enter the nearest metro station`, 'Change lines if required', `Exit near ${to.name}`]
          : ['Metro is limited to select urban corridors. Try Train, Bus or Taxi.'],
        notes: ['Prototype rule: metro shown for Bengaluru-area trips only.'],
        extra: [
          { label: 'Interchange', value: metroPossible ? (straight > 14 ? '1 likely (sample)' : 'None likely') : '—' },
        ],
      },
      bus: {
        available: true,
        distanceKm: road,
        durationMin: busMin,
        fare: inr(busFare),
        fareNote: 'Illustrative estimate',
        summary: `Intercity bus connections from ${from.name} towards ${to.name}.`,
        steps: [`Head to the bus stand in ${from.name}`, 'Board a direct or connecting service', `Get down at ${to.name}`],
        notes: ['Operators and schedules are not shown in this prototype.'],
        extra: [{ label: 'Next departure', value: clock(dep, 45) + ' (sample)' }],
      },
    },
  };
}

// Async so the UI is already shaped for a network call.
export async function getRouteOptions(from, to) {
  await new Promise((r) => setTimeout(r, 450)); // simulate latency for the loading state
  return buildMockRoutes(from, to);
}
