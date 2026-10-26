/**
 * Utility for calculating and formatting intercity travel legs across Karnataka.
 * Deterministic, reliable calculations reusing existing road network data without extra API calls.
 */

export const KARNATAKA_CITIES = {
  bengaluru: { name: 'Bengaluru', lat: 12.9716, lng: 77.5946, region: 'South' },
  bangalore: { name: 'Bengaluru', lat: 12.9716, lng: 77.5946, region: 'South' },
  mysuru: { name: 'Mysuru', lat: 12.2958, lng: 76.6394, region: 'South' },
  mysore: { name: 'Mysuru', lat: 12.2958, lng: 76.6394, region: 'South' },
  hampi: { name: 'Hampi', lat: 15.3350, lng: 76.4600, region: 'Central' },
  hospet: { name: 'Hampi', lat: 15.3350, lng: 76.4600, region: 'Central' },
  badami: { name: 'Badami', lat: 15.9149, lng: 75.6768, region: 'North' },
  belagavi: { name: 'Belagavi', lat: 15.8497, lng: 74.4977, region: 'North' },
  belgaum: { name: 'Belagavi', lat: 15.8497, lng: 74.4977, region: 'North' },
  hubballi: { name: 'Hubballi', lat: 15.3647, lng: 75.1240, region: 'North' },
  hubli: { name: 'Hubballi', lat: 15.3647, lng: 75.1240, region: 'North' },
  mangaluru: { name: 'Mangaluru', lat: 12.9141, lng: 74.8560, region: 'Coastal' },
  mangalore: { name: 'Mangaluru', lat: 12.9141, lng: 74.8560, region: 'Coastal' },
  udupi: { name: 'Udupi', lat: 13.3409, lng: 74.7421, region: 'Coastal' },
  gokarna: { name: 'Gokarna', lat: 14.5479, lng: 74.3188, region: 'Coastal' },
  coorg: { name: 'Coorg (Madikeri)', lat: 12.4244, lng: 75.7382, region: 'Malnad' },
  madikeri: { name: 'Coorg (Madikeri)', lat: 12.4244, lng: 75.7382, region: 'Malnad' },
  chikmagalur: { name: 'Chikkamagaluru', lat: 13.3161, lng: 75.7720, region: 'Malnad' },
  chikkamagaluru: { name: 'Chikkamagaluru', lat: 13.3161, lng: 75.7720, region: 'Malnad' },
  shivamogga: { name: 'Shivamogga', lat: 13.9299, lng: 75.5681, region: 'Malnad' },
  shimoga: { name: 'Shivamogga', lat: 13.9299, lng: 75.5681, region: 'Malnad' },
  vijayapura: { name: 'Vijayapura', lat: 16.8302, lng: 75.7100, region: 'North' },
  bijapur: { name: 'Vijayapura', lat: 16.8302, lng: 75.7100, region: 'North' },
  kalaburagi: { name: 'Kalaburagi', lat: 17.3297, lng: 76.8343, region: 'North' },
  gulbarga: { name: 'Kalaburagi', lat: 17.3297, lng: 76.8343, region: 'North' },
  bidar: { name: 'Bidar', lat: 17.9133, lng: 77.5301, region: 'North' },
  ballari: { name: 'Ballari', lat: 15.1394, lng: 76.9214, region: 'Central' },
  bellary: { name: 'Ballari', lat: 15.1394, lng: 76.9214, region: 'Central' },
  hassan: { name: 'Hassan', lat: 13.0033, lng: 76.1004, region: 'Malnad' },
  davanagere: { name: 'Davanagere', lat: 14.4644, lng: 75.9218, region: 'Central' },
  tumakuru: { name: 'Tumakuru', lat: 13.3379, lng: 77.1173, region: 'South' },
  karwar: { name: 'Karwar', lat: 14.8136, lng: 74.1297, region: 'Coastal' },
  dandeli: { name: 'Dandeli', lat: 15.2427, lng: 74.6190, region: 'North' },
};

/**
 * Pre-calibrated road distances (km) and driving durations (minutes)
 * for major Karnataka travel corridors.
 */
const KNOWN_CORRIDORS = {
  'hubballi-belagavi': { km: 102, min: 115, highway: 'NH 48' },
  'belagavi-hubballi': { km: 102, min: 115, highway: 'NH 48' },
  'bengaluru-mysuru': { km: 145, min: 135, highway: 'Mysuru-Bengaluru Exp / NH 275' },
  'mysuru-bengaluru': { km: 145, min: 135, highway: 'Mysuru-Bengaluru Exp / NH 275' },
  'mysuru-coorg': { km: 120, min: 165, highway: 'NH 275' },
  'coorg-mysuru': { km: 120, min: 165, highway: 'NH 275' },
  'mangaluru-udupi': { km: 55, min: 75, highway: 'NH 66' },
  'udupi-mangaluru': { km: 55, min: 75, highway: 'NH 66' },
  'udupi-gokarna': { km: 178, min: 210, highway: 'NH 66' },
  'gokarna-udupi': { km: 178, min: 210, highway: 'NH 66' },
  'hubballi-hampi': { km: 145, min: 180, highway: 'NH 67' },
  'hampi-hubballi': { km: 145, min: 180, highway: 'NH 67' },
  'hubballi-badami': { km: 105, min: 135, highway: 'SH 34' },
  'badami-hubballi': { km: 105, min: 135, highway: 'SH 34' },
  'badami-hampi': { km: 140, min: 180, highway: 'State Highway' },
  'hampi-badami': { km: 140, min: 180, highway: 'State Highway' },
  'badami-belagavi': { km: 148, min: 195, highway: 'SH 20' },
  'belagavi-badami': { km: 148, min: 195, highway: 'SH 20' },
  'bengaluru-chikkamagaluru': { km: 245, min: 270, highway: 'NH 75 / SH 57' },
  'chikkamagaluru-bengaluru': { km: 245, min: 270, highway: 'NH 75 / SH 57' },
  'bengaluru-shivamogga': { km: 295, min: 330, highway: 'NH 69' },
  'shivamogga-bengaluru': { km: 295, min: 330, highway: 'NH 69' },
  'shivamogga-chikkamagaluru': { km: 95, min: 120, highway: 'NH 173' },
  'chikkamagaluru-shivamogga': { km: 95, min: 120, highway: 'NH 173' },
  'mangaluru-coorg': { km: 135, min: 195, highway: 'NH 275' },
  'coorg-mangaluru': { km: 135, min: 195, highway: 'NH 275' },
  'kalaburagi-vijayapura': { km: 165, min: 195, highway: 'NH 50' },
  'vijayapura-kalaburagi': { km: 165, min: 195, highway: 'NH 50' },
  'vijayapura-badami': { km: 120, min: 150, highway: 'NH 50' },
  'badami-vijayapura': { km: 120, min: 150, highway: 'NH 50' },
  'kalaburagi-bidar': { km: 115, min: 135, highway: 'NH 50' },
  'bidar-kalaburagi': { km: 115, min: 135, highway: 'NH 50' },
};

function normalizeKey(city) {
  if (!city) return '';
  return String(city).toLowerCase().trim().replace(/[^a-z0-9]/g, '');
}

export function getCityInfo(city) {
  const norm = normalizeKey(city);
  return KARNATAKA_CITIES[norm] || {
    name: String(city).replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    lat: null,
    lng: null,
    region: 'Karnataka',
  };
}

export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export function formatDurationMinutes(min) {
  const total = Math.round(Number(min) || 0);
  if (total <= 0) return 'Under 30 min';
  const hours = Math.floor(total / 60);
  const rem = total % 60;
  if (hours === 0) return `${rem} min`;
  return rem ? `${hours} hr ${rem} min` : `${hours} hr`;
}

/**
 * Calculates intercity travel details between two destinations.
 * Returns null if origin and destination are essentially the same city.
 */
export function getIntercityTravelLeg(fromCity, toCity) {
  if (!fromCity || !toCity) return null;

  const key1 = normalizeKey(fromCity);
  const key2 = normalizeKey(toCity);

  if (key1 === key2) return null;

  const corridorKey = `${key1}-${key2}`;
  const fromInfo = getCityInfo(fromCity);
  const toInfo = getCityInfo(toCity);

  // Check pre-calibrated corridor
  if (KNOWN_CORRIDORS[corridorKey]) {
    const data = KNOWN_CORRIDORS[corridorKey];
    return {
      isIntercity: true,
      fromCity: fromInfo.name,
      toCity: toInfo.name,
      distanceKm: data.km,
      durationMinutes: data.min,
      durationText: formatDurationMinutes(data.min),
      highway: data.highway,
      recommendedDeparture: data.min > 180 ? 'Morning (~8:00 AM)' : 'Morning (~9:00 AM) or after early lunch',
      sightseeingAdjustment: `Schedule adjusted for ~${formatDurationMinutes(data.min)} transit plus rest buffer.`,
      hintText: 'Need more route details, transport options, or fare estimates? Explore Route Discovery.',
    };
  }

  // Use coordinate-based model if available
  if (fromInfo.lat && fromInfo.lng && toInfo.lat && toInfo.lng) {
    const crowKm = haversineDistanceKm(fromInfo.lat, fromInfo.lng, toInfo.lat, toInfo.lng);
    if (crowKm < 15) return null; // Same locality

    // In Karnataka, road distance is ~1.22x direct distance in plains, ~1.35x in Western Ghats
    const isGhats = fromInfo.region === 'Malnad' || toInfo.region === 'Malnad';
    const roadFactor = isGhats ? 1.35 : 1.25;
    const estKm = Math.round(crowKm * roadFactor);

    // Speed: ~45 km/h in ghats, ~55 km/h on national/state highways
    const speed = isGhats ? 45 : 55;
    const drivingMinutes = Math.round((estKm / speed) * 60) + 20; // 20m transition buffer

    return {
      isIntercity: true,
      fromCity: fromInfo.name,
      toCity: toInfo.name,
      distanceKm: estKm,
      durationMinutes: drivingMinutes,
      durationText: formatDurationMinutes(drivingMinutes),
      highway: 'National / State Highway',
      recommendedDeparture: drivingMinutes > 180 ? 'Morning (~8:00 AM)' : 'Morning (~9:00 AM) or early afternoon',
      sightseeingAdjustment: `Sightseeing scheduled around ~${formatDurationMinutes(drivingMinutes)} transit and rest time.`,
      hintText: 'Need more route details, transport options, or fare estimates? Explore Route Discovery.',
    };
  }

  // Fallback if coordinates missing
  return {
    isIntercity: true,
    fromCity: fromInfo.name,
    toCity: toInfo.name,
    distanceKm: null,
    durationMinutes: null,
    durationText: 'Approx. 2 - 4 hr drive',
    highway: 'Karnataka Road Network',
    recommendedDeparture: 'Early morning departure recommended',
    sightseeingAdjustment: 'Sightseeing hours adjusted for travel between cities.',
    hintText: 'Need more route details, transport options, or fare estimates? Explore Route Discovery.',
  };
}
