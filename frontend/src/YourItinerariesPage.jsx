/**
 * YourItinerariesPage — lists all saved itineraries for the logged-in user.
 * Allows viewing and deleting saved trips.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ArrowLeft, ArrowRight, BookMarked, CalendarDays, Clock, Compass,
  MapPin, Trash2, Users, Wallet, Loader2, AlertCircle, X
} from 'lucide-react';
import { KaMark, Wordmark } from './components/Logo';
import { useAuth, API_BASE, getAuthHeaders } from './AuthContext';
import './auth.css';

function formatDate(value) {
  if (!value) return '—';
  try {
    const d = new Date(`${value}T12:00:00`);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return value; }
}

function formatCurrency(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return `₹${Math.round(n).toLocaleString('en-IN')}`;
}

function cityLabel(v) {
  return String(v ?? '').replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()).trim() || 'Karnataka';
}

function DeleteConfirm({ title, onConfirm, onCancel, loading }) {
  return (
    <div className="itin-confirm-overlay" role="dialog" aria-modal="true">
      <div className="itin-confirm-box">
        <Trash2 size={24} style={{ color: '#f87171', marginBottom: '0.75rem' }} />
        <h3>Delete itinerary?</h3>
        <p>"{title}" will be permanently removed. This cannot be undone.</p>
        <div className="itin-confirm-actions">
          <button className="itin-confirm-cancel" onClick={onCancel} disabled={loading}>Cancel</button>
          <button className="itin-confirm-delete" onClick={onConfirm} disabled={loading}>
            {loading ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function YourItinerariesPage({ onBack, onViewItinerary, onPlanJourney }) {
  const { user } = useAuth();
  const [itineraries, setItineraries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const fetchItineraries = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/itineraries/saved`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Request failed (${res.status})`);
      }
      setItineraries(await res.json());
    } catch (err) {
      setError(err.message || 'Could not load itineraries.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchItineraries(); }, [fetchItineraries]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/api/itineraries/saved/${deleteTarget.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok && res.status !== 204) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Delete failed.');
      }
      setItineraries((prev) => prev.filter((i) => i.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      alert(err.message || 'Could not delete itinerary.');
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget]);

  return (
    <div className="itineraries-page">
      {/* Top bar */}
      <header className="itineraries-topbar">
        <button type="button" className="itineraries-back" onClick={onBack}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="auth-card__brand" style={{ padding: 0, border: 'none', background: 'none' }}>
          <KaMark size={30} />
          <span className="brand-text">
            <Wordmark />
            <small>Explore. Taste. Travel.</small>
          </span>
        </div>
      </header>

      {/* Hero */}
      <section className="itineraries-hero">
        <p className="itineraries-eyebrow"><span />YOUR ITINERARIES<span /></p>
        <h1 className="itineraries-heading">
          Your saved{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--clr-ochre, #e6920a)' }}>Karnataka</em>{' '}
          journeys
        </h1>
        <p className="itineraries-sub">
          {user?.username ? `Hello, ${user.username}. ` : ''}
          Open any trip to view the full day-by-day schedule — no regeneration needed.
        </p>
      </section>

      {/* Content */}
      <div className="itineraries-content">
        {loading ? (
          <div className="itineraries-loading">
            <Loader2 size={32} />
            <p>Loading your saved journeys…</p>
          </div>
        ) : error ? (
          <div className="itineraries-error">
            <AlertCircle size={28} />
            <p>{error}</p>
            <button
              type="button"
              className="itin-plan-btn"
              onClick={fetchItineraries}
              style={{ marginTop: '0.5rem' }}
            >
              Try again
            </button>
          </div>
        ) : itineraries.length === 0 ? (
          <div className="itineraries-empty">
            <BookMarked size={40} style={{ color: 'rgba(255,255,255,0.2)' }} />
            <p style={{ fontSize: '1.05rem', color: 'rgba(255,255,255,0.6)', fontWeight: 600 }}>
              No saved journeys yet
            </p>
            <p>Generate an itinerary using Plan Your Journey and save it — it will appear here.</p>
            <button type="button" className="itin-plan-btn" onClick={onPlanJourney}>
              <Compass size={16} /> Plan Your Journey
            </button>
          </div>
        ) : (
          <div className="itineraries-grid">
            {itineraries.map((itin) => (
              <article key={itin.id} className="itin-card">
                <div className="itin-card__header">
                  <h2 className="itin-card__title">{itin.title}</h2>
                  <button
                    type="button"
                    className="itin-card__delete-btn"
                    aria-label={`Delete "${itin.title}"`}
                    onClick={() => setDeleteTarget(itin)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>

                {/* Destinations */}
                {itin.destinations?.length > 0 && (
                  <p className="itin-card__destinations">
                    <MapPin size={13} />
                    {itin.destinations.map(cityLabel).join(' → ')}
                  </p>
                )}

                {/* Meta chips */}
                <div className="itin-card__meta">
                  {(itin.start_date || itin.end_date) && (
                    <span className="itin-chip">
                      <CalendarDays size={12} />
                      {formatDate(itin.start_date)}
                      {itin.end_date && itin.end_date !== itin.start_date ? ` – ${formatDate(itin.end_date)}` : ''}
                    </span>
                  )}
                  {itin.duration_days && (
                    <span className="itin-chip">
                      <Clock size={12} />
                      {itin.duration_days} day{itin.duration_days !== 1 ? 's' : ''}
                    </span>
                  )}
                  {itin.traveller_count && (
                    <span className="itin-chip">
                      <Users size={12} />
                      {itin.traveller_count} traveller{itin.traveller_count !== 1 ? 's' : ''}
                    </span>
                  )}
                  {itin.total_budget && (
                    <span className="itin-chip">
                      <Wallet size={12} />
                      {formatCurrency(itin.total_budget)}
                    </span>
                  )}
                  {itin.travel_style && (
                    <span className="itin-chip" style={{ textTransform: 'capitalize' }}>
                      {itin.travel_style}
                    </span>
                  )}
                </div>

                <p className="itin-card__saved-at">
                  Saved {formatDate(itin.created_at?.slice(0, 10))}
                </p>

                <button
                  type="button"
                  className="itin-card__view-btn"
                  onClick={() => onViewItinerary(itin.id)}
                >
                  View Itinerary <ArrowRight size={15} />
                </button>
              </article>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      {deleteTarget && (
        <DeleteConfirm
          title={deleteTarget.title}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </div>
  );
}
