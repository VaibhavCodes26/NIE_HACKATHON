
import { useEffect, useRef, useState } from 'react';
import { setOptions, importLibrary } from '@googlemaps/js-api-loader';
import { MapPin, AlertCircle, Loader2 } from 'lucide-react';

let loaderConfigured = false;
let mapsPromise;

function loadGoogleMaps() {
  if (!mapsPromise) {
    if (!loaderConfigured) {
      setOptions({
        key: import.meta.env.VITE_MAPS_JS_API_KEY,
        v: 'weekly',
      });
      loaderConfigured = true;
    }

    mapsPromise = importLibrary('maps');
  }

  return mapsPromise;
}

function decodePolyline(encoded) {
  if (!encoded || typeof encoded !== 'string') return [];
  const points = [];
  let index = 0;
  const len = encoded.length;
  let lat = 0;
  let lng = 0;

  while (index < len) {
    let b;
    let shift = 0;
    let result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = (result & 1) ? ~(result >> 1) : (result >> 1);
    lat += dlat;

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = (result & 1) ? ~(result >> 1) : (result >> 1);
    lng += dlng;

    points.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }

  return points;
}

export default function RouteMap({ from, to, modeId, polyline }) {
  const mapElement = useRef(null);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    let activeMap = null;
    let activePolyline = null;
    const markers = [];

    async function initializeMap() {
      if (
        !import.meta.env.VITE_MAPS_JS_API_KEY ||
        !from ||
        !to ||
        !Number.isFinite(Number(from.lat)) ||
        !Number.isFinite(Number(from.lng)) ||
        !Number.isFinite(Number(to.lat)) ||
        !Number.isFinite(Number(to.lng))
      ) {
        setStatus('error');
        return;
      }

      setStatus('loading');

      try {
        const { Map } = await loadGoogleMaps();

        if (cancelled || !mapElement.current) return;

        const origin = {
          lat: Number(from.lat),
          lng: Number(from.lng),
        };

        const destination = {
          lat: Number(to.lat),
          lng: Number(to.lng),
        };

        activeMap = new Map(mapElement.current, {
          center: origin,
          zoom: 7,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          clickableIcons: false,
          gestureHandling: 'cooperative',
        });

        const bounds = new window.google.maps.LatLngBounds();
        bounds.extend(origin);
        bounds.extend(destination);

        const decodedPoints = decodePolyline(polyline);

        if (decodedPoints.length > 0) {
          activePolyline = new window.google.maps.Polyline({
            path: decodedPoints,
            strokeColor: modeId === 'walking' ? '#0284c7' : '#b42318',
            strokeWeight: 5,
            strokeOpacity: 0.85,
            map: activeMap,
          });

          decodedPoints.forEach((point) => bounds.extend(point));
        } else {
          // Fallback direct connector
          activePolyline = new window.google.maps.Polyline({
            path: [origin, destination],
            strokeColor: '#b42318',
            strokeWeight: 3,
            strokeOpacity: 0.6,
            map: activeMap,
          });
        }

        const markerA = new window.google.maps.Marker({
          position: origin,
          map: activeMap,
          title: from.name,
          label: {
            text: 'A',
            color: '#ffffff',
            fontWeight: '700',
          },
        });
        markers.push(markerA);

        const markerB = new window.google.maps.Marker({
          position: destination,
          map: activeMap,
          title: to.name,
          label: {
            text: 'B',
            color: '#ffffff',
            fontWeight: '700',
          },
        });
        markers.push(markerB);

        activeMap.fitBounds(bounds, { top: 35, right: 35, bottom: 35, left: 35 });
        setStatus('ready');
      } catch (error) {
        console.error('Google Maps initialization failed:', error);
        if (!cancelled) setStatus('error');
      }
    }

    initializeMap();

    return () => {
      cancelled = true;
      if (activePolyline) activePolyline.setMap(null);
      markers.forEach((m) => m.setMap(null));
    };
  }, [from?.lat, from?.lng, to?.lat, to?.lng, modeId, polyline]);

  return (
    <section className="rd-route-map" aria-label="Journey map">
      <div className="rd-route-map__heading">
        <div>
          <span className="rd-route-map__eyebrow">YOUR ROUTE</span>
          <h3>Journey map</h3>
        </div>
        <MapPin size={19} aria-hidden="true" />
      </div>

      <div className="rd-route-map__viewport">
        <div
          ref={mapElement}
          className="rd-route-map__canvas"
          aria-label={`Map from ${from?.name || 'origin'} to ${
            to?.name || 'destination'
          }`}
        />

        {status === 'loading' && (
          <div className="rd-route-map__message">
            <Loader2 className="rd-route-map__spinner" size={20} />
            <span>Loading route map…</span>
          </div>
        )}

        {status === 'error' && (
          <div className="rd-route-map__message rd-route-map__message--error">
            <AlertCircle size={21} />
            <div>
              <strong>Map route unavailable</strong>
              <p>
                Google Maps could not calculate this route. Check the
                map API settings or try another transport mode.
              </p>
            </div>
          </div>
        )}
      </div>

      <p className="rd-route-map__caption">
        Map directions are provided by Google Maps. Transit routes may
        not be available for every journey.
      </p>
    </section>
  );
}
