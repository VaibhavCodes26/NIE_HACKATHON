import { useState } from 'react';
import { Globe, Menu, X } from 'lucide-react';
import { KaMark, Wordmark } from './Logo';
import { useI18n } from '../i18n';
import { LANGS } from '../data/translations';

export default function Navbar({ active, onNav }) {
  const { t, lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const items = [
    ['plan', 'nav.plan'],
    ['food', 'nav.food'],
    ['drishti', 'nav.drishti'],
    ['help', 'nav.help'],
    ['about', 'nav.about'],
  ];
  const go = (id) => { setOpen(false); onNav(id); };

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
        </nav>

        <div className="header-right">
          <label className="lang">
            <Globe size={18} aria-hidden="true" />
            <span className="sr-only">{t('lang.label')}</span>
            <select value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </label>
          <button className="menu-btn" aria-label={t('nav.menu')} aria-expanded={open} aria-controls="main-nav" onClick={() => setOpen(!open)}>
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>
    </header>
  );
}
