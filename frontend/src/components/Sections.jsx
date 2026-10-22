import { Utensils, Route } from 'lucide-react';
import { DISHES } from '../data/content';
import { DESTINATIONS, commonsPage } from '../data/destinations';
import { CATEGORIES } from '../data/content';
import { useI18n } from '../i18n';

export function FoodSection() {
  const { t } = useI18n();
  return (
    <section id="food" className="section section-sand">
      <div className="container">
        <header className="section-head">
          <h2>{t('food.title')}</h2>
          <p>{t('food.intro')}</p>
        </header>
        <ul className="dishes">
          {DISHES.map((d) => (
            <li key={d.id} className="dish">
              <span className="dish-icon" aria-hidden="true"><Utensils size={22} /></span>
              <h3>{d.name}</h3>
              <p>{d.note}</p>
              <small>{t('food.nophoto')}</small>
            </li>
          ))}
        </ul>
        <p className="notice"><Route size={18} aria-hidden="true" /> {t('food.soon')}</p>
      </div>
    </section>
  );
}

export function AboutSection() {
  const { t } = useI18n();
  return (
    <section id="about" className="section">
      <div className="container about">
        <h2>{t('about.title')}</h2>
        <p>{t('about.body')}</p>
        <p className="notice">{t('about.ai')}</p>
      </div>
    </section>
  );
}

export function Footer() {
  const { t } = useI18n();
  const files = [...DESTINATIONS.map((d) => [d.name, d.file])];
  return (
    <footer className="footer">
      <div className="container">
        <p className="footer-note">{t('footer.note')}</p>
        <details className="credits">
          <summary>{t('footer.credits')}</summary>
          <ul>
            {files.map(([n, f]) => (
              <li key={f}>{n}: <a href={commonsPage(f)} target="_blank" rel="noreferrer">Wikimedia Commons file page</a></li>
            ))}
            {CATEGORIES.filter((c) => c.file && !files.some((x) => x[1] === c.file)).map((c) => (
              <li key={c.id}><a href={c.credit} target="_blank" rel="noreferrer">{c.id}</a></li>
            ))}
            <li>State outline: GADM-derived India admin boundaries (Karnataka), simplified for display. GADM data is free for non-commercial use with attribution — see gadm.org/license.</li>
          </ul>
        </details>
      </div>
    </footer>
  );
}
