/**
 * LoginPage — NammaPrayana login with username/password and Google OAuth.
 * Matches the existing Karnataka-inspired visual design.
 */

import { useState, useCallback } from 'react';
import { ArrowLeft, Eye, EyeOff, LogIn, User, Lock, AlertCircle, Loader2 } from 'lucide-react';
import { KaMark, Wordmark } from './components/Logo';
import { useAuth, API_BASE } from './AuthContext';
import './auth.css';

export default function LoginPage({ onBack, onSignup, onSuccess }) {
  const { login, googleClientId } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!form.username.trim() || !form.password) {
      setError('Please enter your username and password.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: form.username.trim(), password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Login failed. Please check your credentials.');
        return;
      }
      login(data);
      onSuccess?.(data);
    } catch {
      setError('Could not connect to the server. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [form, login, onSuccess]);

  const handleGoogle = useCallback(async () => {
    const clientId = googleClientId || import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setError('Google sign-in is not configured. Set GOOGLE_CLIENT_ID in backend/.env or frontend/.env.local.');
      return;
    }
    setGoogleLoading(true);
    setError('');
    try {
      // Ensure Google Identity Services script is available
      if (!window.google?.accounts?.id) {
        await new Promise((resolve, reject) => {
          if (window.google?.accounts?.id) return resolve();
          let s = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
          if (!s) {
            s = document.createElement('script');
            s.src = 'https://accounts.google.com/gsi/client';
            s.async = true;
            s.defer = true;
            document.head.appendChild(s);
          }
          s.addEventListener('load', () => resolve(), { once: true });
          s.addEventListener('error', () => reject(new Error('Failed to load Google Identity Services')), { once: true });
          setTimeout(() => {
            if (window.google?.accounts?.id) resolve();
            else reject(new Error('Google sign-in script timed out'));
          }, 3500);
        });
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            const res = await fetch(`${API_BASE}/api/auth/google`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ id_token: response.credential }),
            });
            const data = await res.json();
            if (!res.ok) {
              setError(data.detail || 'Google sign-in failed.');
              return;
            }
            login(data);
            onSuccess?.(data);
          } catch {
            setError('Google sign-in failed. Please try again.');
          } finally {
            setGoogleLoading(false);
          }
        },
      });

      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          setGoogleLoading(false);
          const reason = notification.getNotDisplayedReason?.() || notification.getSkippedReason?.() || '';
          if (reason) {
            console.warn('Google One Tap notice:', reason);
          }
        }
      });
    } catch (err) {
      setError(err?.message || 'Google sign-in is unavailable. Use username and password instead.');
      setGoogleLoading(false);
    }
  }, [googleClientId, login, onSuccess]);

  return (
    <div className="auth-page">
      <div className="auth-page__bg" aria-hidden="true" />

      <div className="auth-card">
        {/* Header */}
        <div className="auth-card__brand">
          <button
            type="button"
            className="auth-back-btn"
            onClick={onBack}
            aria-label="Back to home"
          >
            <ArrowLeft size={17} />
          </button>
          <KaMark size={36} />
          <span className="brand-text">
            <Wordmark />
            <small>Explore. Taste. Travel.</small>
          </span>
        </div>

        <div className="auth-card__body">
          <p className="auth-eyebrow"><span />WELCOME BACK<span /></p>
          <h1 className="auth-title">Sign in to your account</h1>
          <p className="auth-subtitle">
            Continue planning your Karnataka adventure.
          </p>

          {error && (
            <div className="auth-error" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="auth-field">
              <label htmlFor="login-username">Username</label>
              <div className="auth-input-wrap">
                <User size={16} className="auth-input-icon" aria-hidden="true" />
                <input
                  id="login-username"
                  type="text"
                  autoComplete="username"
                  value={form.username}
                  onChange={set('username')}
                  placeholder="Your username"
                  disabled={loading}
                  required
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="login-password">Password</label>
              <div className="auth-input-wrap">
                <Lock size={16} className="auth-input-icon" aria-hidden="true" />
                <input
                  id="login-password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={form.password}
                  onChange={set('password')}
                  placeholder="Your password"
                  disabled={loading}
                  required
                />
                <button
                  type="button"
                  className="auth-pw-toggle"
                  onClick={() => setShowPw((v) => !v)}
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              id="login-submit-btn"
              type="submit"
              className="auth-btn auth-btn--primary"
              disabled={loading}
            >
              {loading ? <Loader2 size={17} className="auth-spin" /> : <LogIn size={17} />}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="auth-divider"><span>or</span></div>

          <button
            id="login-google-btn"
            type="button"
            className="auth-btn auth-btn--google"
            onClick={handleGoogle}
            disabled={googleLoading || loading}
          >
            {googleLoading ? (
              <Loader2 size={17} className="auth-spin" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
                <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
              </svg>
            )}
            Continue with Google
          </button>

          <p className="auth-switch">
            Don&apos;t have an account?{' '}
            <button type="button" className="auth-link" onClick={onSignup}>
              Sign up
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
