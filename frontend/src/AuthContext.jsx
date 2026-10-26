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
  const token = sessionStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [googleClientId, setGoogleClientId] = useState(
    () => import.meta.env.VITE_GOOGLE_CLIENT_ID || null
  );

  // Check the backend session on mount / refresh within the current tab.
  const refresh = useCallback(async () => {
    // Tab-scoped: if this tab has no token in sessionStorage, do not authenticate
    const token = typeof window !== 'undefined' ? sessionStorage.getItem(TOKEN_KEY) : null;
    if (!token) {
      setUser(null);
      setAuthLoading(false);
      return;
    }

    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        sessionStorage.removeItem(TOKEN_KEY);
        try { localStorage.removeItem(TOKEN_KEY); } catch {}
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    // Proactively purge any legacy localStorage tokens from previous persistent sessions
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {}
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
      sessionStorage.setItem(TOKEN_KEY, userData.token);
    }
    // Purge any lingering localStorage token
    try { localStorage.removeItem(TOKEN_KEY); } catch {}
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
    } catch {
      // Ignore network errors on logout.
    }
    sessionStorage.removeItem(TOKEN_KEY);
    try { localStorage.removeItem(TOKEN_KEY); } catch {}
    setUser(null);
  }, []);

  const authFetch = useCallback((url, options = {}) => {
    const headers = {
      ...options.headers,
      ...getAuthHeaders(),
    };
    return fetch(url, { ...options, headers });
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
