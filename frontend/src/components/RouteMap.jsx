
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

    mapsPromise = Promise.all([
      importLibrary('maps'),
      importLibrary('routes'),
    ]);
  }

  return mapsPromise;
}

const MODE_CONFIG = {
  taxi: {
    travelMode: 'DRIVING',
  },
  walking: {
    travelMode: 'WALKING',
  },
  bus: {
    travelMode: 'TRANSIT',
    transitMode: 'BUS',
  },
  metro: {
    travelMode: 'TRANSIT',
    transitMode: 'SUBWAY',
  },
};

export default function RouteMap({ from, to, modeId }) {
  const mapElement = useRef(null);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    let renderer;

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
        const [{ Map }, { DirectionsService, DirectionsRenderer }] =
          await loadGoogleMaps();

        if (cancelled || !mapElement.current) return;

        const origin = {
          lat: Number(from.lat),
          lng: Number(from.lng),
        };

        const destination = {
          lat: Number(to.lat),
          lng: Number(to.lng),
        };

        const map = new Map(mapElement.current, {
          center: origin,
          zoom: 7,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          clickableIcons: false,
          gestureHandling: 'cooperative',
        });

        renderer = new DirectionsRenderer({
          map,
          suppressMarkers: false,
          preserveViewport: false,
          polylineOptions: {
            strokeColor: '#B42318',
            strokeWeight: 5,
            strokeOpacity: 0.85,
          },
        });

        const config = MODE_CONFIG[modeId];

        if (!config) {
          setStatus('error');
          return;
        }

        const request = {
          origin,
          destination,
          travelMode: config.travelMode,
        };

        if (config.transitMode) {
          request.transitOptions = {
            modes: [
              window.google.maps.TransitMode[config.transitMode],
            ],
          };
        }

        const service = new DirectionsService();

        service.route(request, (result, responseStatus) => {
          if (cancelled) return;

          if (
            responseStatus ===
              window.google.maps.DirectionsStatus.OK &&
            result
          ) {
            renderer.setDirections(result);
            setStatus('ready');
          } else {
            setStatus('error');
          }
        });
      } catch (error) {
        console.error('Google Maps loading failed:', error);
        if (!cancelled) setStatus('error');
      }
    }

    initializeMap();

    return () => {
      cancelled = true;
      if (renderer) renderer.setMap(null);
    };
  }, [from?.lat, from?.lng, to?.lat, to?.lng, modeId]);

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
