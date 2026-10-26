/**
 * LoginRequiredModal — shown when an unauthenticated visitor clicks a
 * protected feature. Stays on the landing page; the user can log in,
 * sign up, or close the modal.
 */

import { Lock } from 'lucide-react';
import '../auth.css';

export default function LoginRequiredModal({ onLogin, onSignup, onClose }) {
  return (
    <div
      className="auth-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-required-title"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="auth-modal">
        <button
          type="button"
          className="auth-modal__close"
          aria-label="Close"
          onClick={onClose}
        >
          ✕
        </button>

        <div className="auth-modal__icon">
          <Lock size={24} />
        </div>

        <h2 id="login-required-title" className="auth-modal__title">
          Login Required
        </h2>

        <p className="auth-modal__body">
          Please log in or create an account to access NammaPrayana&apos;s travel
          planning, food discovery, Kannada assistance, visual assistance, and saved
          itineraries.
        </p>

        <div className="auth-modal__actions">
          <button
            id="login-required-login-btn"
            type="button"
            className="auth-btn auth-btn--primary"
            onClick={onLogin}
          >
            Log In
          </button>
          <button
            id="login-required-signup-btn"
            type="button"
            className="auth-btn auth-btn--google"
            onClick={onSignup}
          >
            Sign Up
          </button>
          <button
            id="login-required-cancel-btn"
            type="button"
            className="auth-btn auth-btn--ghost"
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
