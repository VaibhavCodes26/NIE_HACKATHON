import { useState, useRef, useEffect } from 'react';
import { Globe, Menu, X, LogOut, BookMarked, ChevronDown } from 'lucide-react';
import { KaMark, Wordmark } from './Logo';
import { useI18n } from '../i18n';
import { LANGS } from '../data/translations';
import '../auth.css';

export default function Navbar({ active, onNav, user, onLogin, onSignup, onLogout, onYourItineraries }) {
  const { t, lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);

  const items = [
    ['plan', 'nav.plan'],
    ['food', 'nav.food'],
    ['drishti', 'nav.drishti'],
    ['about', 'nav.about'],
  ];
  const go = (id) => { setOpen(false); onNav(id); };

  // Close user dropdown when clicking outside
  useEffect(() => {
    const handleClick = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
    };
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClick);
    }
    return () => document.removeEventListener('mousedown', handleClick);
  }, [userMenuOpen]);

  const handleLogout = async () => {
    setUserMenuOpen(false);
    setOpen(false);
    await onLogout?.();
  };

  return (
    <header className="header">
      <div className="container header-in">
        <a className="brand" href="#home" onClick={(e) => { e.preventDefault(); go('home'); }} aria-label="NammaPrayana — home">
          <KaMark size={38} />
          <span className="brand-text">
            <Wordmark />
            <small>{t('tagline')}</small>
          </span>
        </a>

        <nav id="main-nav" className={`nav ${open ? 'open' : ''}`} aria-label="Main">
          {items.map(([id, key]) => (
            <button key={id} className="nav-link" aria-current={active === id ? 'page' : undefined} onClick={() => go(id)}>
              {t(key)}
            </button>
          ))}
          {/* Your Itineraries nav link — only when logged in */}
          {user && (
            <button
              className="nav-link"
              aria-current={active === 'itineraries' ? 'page' : undefined}
              onClick={() => { setOpen(false); onYourItineraries?.(); }}
            >
              Your Itineraries
            </button>
          )}
        </nav>

        <div className="header-right">
          <label className="lang">
            <Globe size={18} aria-hidden="true" />
            <span className="sr-only">{t('lang.label')}</span>
            <select value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </label>

          {/* Auth area */}
          {user ? (
            <div className="nav-user-menu" ref={userMenuRef}>
              <button
                type="button"
                className="nav-user-btn"
                onClick={() => setUserMenuOpen((v) => !v)}
                aria-expanded={userMenuOpen}
                aria-haspopup="menu"
              >
                <span className="user-avatar" aria-hidden="true">
                  {user.username?.[0]?.toUpperCase() ?? 'U'}
                </span>
                <span className="user-name">{user.username}</span>
                <ChevronDown size={13} style={{ opacity: 0.6, transform: userMenuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
              </button>

              {userMenuOpen && (
                <div className="nav-user-dropdown" role="menu">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => { setUserMenuOpen(false); onYourItineraries?.(); }}
                  >
                    <BookMarked size={15} /> Your Itineraries
                  </button>
                  <div className="nav-dropdown-divider" />
                  <button
                    type="button"
                    role="menuitem"
                    className="logout-btn"
                    onClick={handleLogout}
                  >
                    <LogOut size={15} /> Log Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="nav-auth-buttons">
              <button
                id="nav-login-btn"
                type="button"
                className="nav-login-btn"
                onClick={onLogin}
              >
                Log In
              </button>
              <button
                id="nav-signup-btn"
                type="button"
                className="nav-signup-btn"
                onClick={onSignup}
              >
                Sign Up
              </button>
            </div>
          )}

          <button className="menu-btn" aria-label={t('nav.menu')} aria-expanded={open} aria-controls="main-nav" onClick={() => setOpen(!open)}>
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>
    </header>
  );
}
