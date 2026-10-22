
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import {
  ChevronDown,
  MapPin,
  Flag,
  X,
  Loader2,
  Search,
} from 'lucide-react';

const ICONS = { start: MapPin, end: Flag };

const TYPE_LABEL = {
  city: 'City',
  landmark: 'Landmark',
  region: 'Region',
  station: 'Station',
  custom: 'Location',
  country: 'Country',
  street: 'Address',
};

const API_KEY = import.meta.env.VITE_GEOAPIFY_API_KEY;

export default function LocationField({
  variant = 'start',
  label,
  placeholder,
  options = [],
  value,
  onChange,
  error,
}) {
  const uid = useId();
  const listId = `${uid}-list`;
  const Icon = ICONS[variant] || MapPin;
  const wrapRef = useRef(null);
  const inputRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [remoteOptions, setRemoteOptions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');

  const text = open ? query : value?.name ?? '';

  // Keep existing curated Karnataka locations searchable.
  const localOptions = useMemo(() => {
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);

    if (words.length === 0) return options;

    return options.filter((option) => {
      const searchableText =
        `${option.name} ${option.hint ?? ''} ${option.id}`.toLowerCase();

      return words.every((word) => searchableText.includes(word));
    });
  }, [options, query]);

  // Search real places across India using Geoapify.
  useEffect(() => {
    const searchText = query.trim();

    setRemoteOptions([]);
    setSearchError('');

    if (!open || searchText.length < 3) {
      setSearching(false);
      return undefined;
    }

    if (!API_KEY) {
      setSearching(false);
      setSearchError(
        'India-wide search needs a Geoapify API key. Configure VITE_GEOAPIFY_API_KEY in frontend/.env.local.'
      );
      return undefined;
    }

    const controller = new AbortController();

    // Debounce requests while the user is typing.
    const timeoutId = setTimeout(async () => {
      setSearching(true);

      try {
        const params = new URLSearchParams({
          text: searchText,
          filter: 'countrycode:in',
          format: 'json',
          limit: '8',
          apiKey: API_KEY,
        });

        const response = await fetch(
          `https://api.geoapify.com/v1/geocode/autocomplete?${params}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error(
            response.status === 429
              ? 'Location search limit reached. Please try again shortly.'
              : 'Unable to search locations right now.'
          );
        }

        const data = await response.json();

        const results = (data.results || [])
          .filter(
            (place) =>
              Number.isFinite(Number(place.lat)) &&
              Number.isFinite(Number(place.lon)) &&
              place.country_code?.toLowerCase() === 'in'
          )
          .map((place, index) => {
            const name =
              place.address_line1 ||
              place.name ||
              place.city ||
              place.formatted;

            const context = [
              place.city && place.city !== name ? place.city : null,
              place.state,
              place.country,
            ]
              .filter(Boolean)
              .join(', ');

            const resultType = place.result_type || place.category;

            let type = 'custom';

            if (
              resultType === 'city' ||
              resultType === 'suburb' ||
              resultType === 'district'
            ) {
              type = 'city';
            } else if (
              resultType === 'street' ||
              resultType === 'building' ||
              resultType === 'amenity'
            ) {
              type = 'street';
            } else if (
              resultType === 'station' ||
              /station|railway/i.test(name || '')
            ) {
              type = 'station';
            } else if (resultType === 'state') {
              type = 'region';
            }

            return {
              id: `geo-${place.place_id || `${place.lat}-${place.lon}-${index}`}`,
              name: name || place.formatted,
              type,
              hint: context || place.formatted,
              lat: Number(place.lat),
              lng: Number(place.lon),
              formatted: place.formatted,
              source: 'geoapify',
            };
          });

        if (!controller.signal.aborted) {
          setRemoteOptions(results);
        }
      } catch (requestError) {
        if (
          requestError.name !== 'AbortError' &&
          !controller.signal.aborted
        ) {
          setSearchError(
            requestError.message || 'Location search failed.'
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setSearching(false);
        }
      }
    }, 350);

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [query, open]);

  // Combine local options and live search results without duplicates.
  const filtered = useMemo(() => {
    const combined = [...localOptions];
    const existingNames = new Set(
      localOptions.map((option) => option.name.trim().toLowerCase())
    );

    remoteOptions.forEach((option) => {
      const key = option.name.trim().toLowerCase();

      if (!existingNames.has(key)) {
        combined.push(option);
        existingNames.add(key);
      }
    });

    return combined;
  }, [localOptions, remoteOptions]);

  useEffect(() => {
    const onDoc = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) {
        setOpen(false);
        setQuery('');
      }
    };

    document.addEventListener('mousedown', onDoc);

    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  useEffect(() => {
    setActive(0);
  }, [query, open, filtered.length]);

  const select = (option) => {
    onChange(option);
    setOpen(false);
    setQuery('');
    setRemoteOptions([]);
    setSearchError('');
  };

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();

      if (!open) {
        setOpen(true);
      } else {
        setActive((index) => Math.min(index + 1, filtered.length - 1));
      }
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === 'Enter' && open) {
      event.preventDefault();

      if (filtered[active]) {
        select(filtered[active]);
      }
    } else if (event.key === 'Escape') {
      setOpen(false);
      setQuery('');
    }
  };

  const clearSelection = (event) => {
    event.stopPropagation();
    onChange(null);
    setQuery('');
    setRemoteOptions([]);
    setOpen(true);
    inputRef.current?.focus();
  };

  return (
    <div
      ref={wrapRef}
      className={`rd-field rd-field--${variant} ${
        error ? 'is-error' : ''
      } ${open ? 'is-open' : ''}`}
    >
      <label className="rd-field__label" htmlFor={`${uid}-input`}>
        {label}
      </label>

      <div
        className="rd-field__control"
        onClick={() => inputRef.current?.focus()}
      >
        <span className="rd-field__icon" aria-hidden="true">
          <Icon size={20} />
        </span>

        <input
          id={`${uid}-input`}
          ref={inputRef}
          className="rd-field__input"
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-invalid={!!error}
          aria-describedby={error ? `${uid}-err` : undefined}
          aria-activedescendant={
            open && filtered[active]
              ? `${uid}-opt-${filtered[active].id}`
              : undefined
          }
          autoComplete="off"
          placeholder={placeholder}
          value={text}
          onFocus={() => {
            setQuery('');
            setOpen(true);
          }}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />

        {searching ? (
          <Loader2 size={17} className="rd-spin" aria-label="Searching" />
        ) : value && !open ? (
          <button
            type="button"
            className="rd-field__btn"
            aria-label={`Clear ${label}`}
            onClick={clearSelection}
          >
            <X size={16} />
          </button>
        ) : (
          <ChevronDown
            size={18}
            className="rd-field__chev"
            aria-hidden="true"
          />
        )}
      </div>

      {open && (
        <ul id={listId} role="listbox" className="rd-menu">
          {query.trim().length < 3 && localOptions.length === 0 && (
            <li className="rd-menu__empty">
              Type at least 3 characters to search locations across India.
            </li>
          )}

          {filtered.map((option, index) => (
            <li
              key={option.id}
              id={`${uid}-opt-${option.id}`}
              role="option"
              aria-selected={value?.id === option.id}
              className={`rd-menu__item ${
                index === active ? 'is-active' : ''
              } ${value?.id === option.id ? 'is-selected' : ''}`}
              onMouseEnter={() => setActive(index)}
              onMouseDown={(event) => {
                event.preventDefault();
                select(option);
              }}
            >
              <span className="rd-menu__pin" aria-hidden="true">
                {option.source === 'geoapify' ? (
                  <Search size={15} />
                ) : (
                  <Icon size={15} />
                )}
              </span>

              <span className="rd-menu__text">
                <strong>{option.name}</strong>
                {option.hint && <small>{option.hint}</small>}
              </span>

              {option.type && (
                <em className="rd-menu__tag">
                  {TYPE_LABEL[option.type] ?? 'Location'}
                </em>
              )}
            </li>
          ))}

          {searching && (
            <li className="rd-menu__empty">
              Searching places in India…
            </li>
          )}

          {!searching &&
            query.trim().length >= 3 &&
            filtered.length === 0 &&
            !searchError && (
              <li className="rd-menu__empty">
                No matching places found. Try another spelling.
              </li>
            )}

          {searchError && (
            <li className="rd-menu__empty" role="status">
              {searchError}
            </li>
          )}

          {query.trim().length < 3 && localOptions.length > 0 && (
            <li className="rd-menu__empty">
              Type 3 or more characters to search all of India.
            </li>
          )}
        </ul>
      )}

      {error && (
        <p id={`${uid}-err`} className="rd-field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
