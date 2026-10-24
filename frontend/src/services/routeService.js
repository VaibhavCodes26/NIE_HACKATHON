

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

export function formatDuration(min) {
  const value = Number(min);

  if (!Number.isFinite(value) || value < 0) {
    return 'Unavailable';
  }

  const minutes = Math.round(value);

  if (minutes < 60) return `${minutes} min`;

  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;

  return remaining
    ? `${hours} hr ${remaining} min`
    : `${hours} hr`;
}

export function haversineKm(a, b) {
  const earthRadiusKm = 6371;
  const toRad = (degrees) => (degrees * Math.PI) / 180;

  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);

  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) *
      Math.cos(toRad(b.lat)) *
      Math.sin(dLng / 2) ** 2;

  return (
    2 *
    earthRadiusKm *
    Math.asin(Math.sqrt(Math.min(1, h)))
  );
}

/**
 * Sends the source and destination already selected on Route Discovery
 * to the FastAPI backend. No second form or manual re-entry is needed.
 */
export async function getRouteOptions(from, to) {
  if (!from || !to) {
    throw new Error('Please select a source and destination.');
  }

  if (
    !Number.isFinite(Number(from.lat)) ||
    !Number.isFinite(Number(from.lng)) ||
    !Number.isFinite(Number(to.lat)) ||
    !Number.isFinite(Number(to.lng))
  ) {
    throw new Error(
      'Coordinates are missing for the selected source or destination.'
    );
  }

  const requestBody = {
    origin: {
      id: String(from.id),
      name: from.name,
      lat: Number(from.lat),
      lng: Number(from.lng),
    },
    destination: {
      id: String(to.id),
      name: to.name,
      lat: Number(to.lat),
      lng: Number(to.lng),
    },
  };

  const response = await fetch(`${API_BASE}/api/routes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    let message = `Route API request failed (${response.status}).`;

    try {
      const errorData = await response.json();

      if (errorData.detail) {
        message =
          typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
      }
    } catch {
      // Keep the default error if the response is not JSON.
    }

    throw new Error(message);
  }

  const data = await response.json();

  if (!data || !data.modes) {
    throw new Error(
      'The route API returned an unexpected response.'
    );
  }

  // Return the real backend response without fabricating route details.
  return data;
}
