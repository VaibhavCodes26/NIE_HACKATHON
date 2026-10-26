/**
 * AuthContext — centralized authentication state for NammaPrayana.
 *
 * Provides:
 *   - user          : the authenticated user object (or null)
 *   - authLoading   : true while the initial session check is in progress
 *   - login         : call after successful login to set state & token
 *   - logout        : clears state & token and calls the backend logout endpoint
 *   - refresh       : re-checks the backend session (e.g. after signup / refresh)
 *   - googleClientId: public Google OAuth client ID
 *   - authFetch     : fetch wrapper that automatically attaches credentials & Bearer token
 *   - getAuthHeaders: helper returning { Authorization: 'Bearer ...' }
 *
 * Supports both HttpOnly cookies and Bearer token in the Authorization header.
 * This guarantees reliable authentication even across localhost vs 127.0.0.1
 * domain boundaries where browsers restrict cross-site cookies.
 */

import { createContext, useCallback, useContext, useEffect, useState } from 'react';

const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }
  return 'http://127.0.0.1:8000';
};

const API_BASE = getApiBase();
const TOKEN_KEY = 'np_auth_token';

export function getAuthHeaders() {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [googleClientId, setGoogleClientId] = useState(
    () => import.meta.env.VITE_GOOGLE_CLIENT_ID || null
  );

  // Check the backend session on every mount (page load / refresh).
  const refresh = useCallback(async () => {
    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        localStorage.removeItem(TOKEN_KEY);
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Load public auth configuration from backend
  useEffect(() => {
    fetch(`${API_BASE}/api/auth/config`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((cfg) => {
        if (cfg.google_client_id) {
          setGoogleClientId(cfg.google_client_id);
        }
      })
      .catch(() => {});
  }, []);

  const login = useCallback((userData) => {
    if (userData?.token) {
      localStorage.setItem(TOKEN_KEY, userData.token);
    }
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
      });
    } catch {
      // Ignore network errors on logout.
    }
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  const authFetch = useCallback((url, options = {}) => {
    const headers = {
      ...options.headers,
      ...getAuthHeaders(),
    };
    return fetch(url, { ...options, headers, credentials: 'include' });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        authLoading,
        login,
        logout,
        refresh,
        googleClientId,
        authFetch,
        getAuthHeaders,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export { API_BASE };
