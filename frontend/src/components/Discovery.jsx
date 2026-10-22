import { Landmark, Mountain, UtensilsCrossed, Drama, Waves, Castle } from 'lucide-react';
import Img from './Img';
import { CATEGORIES } from '../data/content';
import { useI18n } from '../i18n';

export const ICONS = { Landmark, Mountain, UtensilsCrossed, Drama, Waves, Castle };

export default function Discovery({ onCategory }) {
  const { t } = useI18n();
  return (
    <section id="discover" className="section">
      <div className="container">
        <header className="section-head">
          <h2>{t('disc.title')}</h2>
          <p>{t('disc.sub')}</p>
        </header>
        <ul className="cards">
          {CATEGORIES.map((c) => {
            const Icon = ICONS[c.icon];
            return (
              <li key={c.id}>
                <button className="card" onClick={() => onCategory(c.id)}>
                  {c.img ? (
                    <Img src={c.img} alt="" className="card-img" label="" />
                  ) : (
                    <div className="card-art" style={{ background: `linear-gradient(155deg, ${c.tone[0]}, ${c.tone[1]})` }} aria-hidden="true">
                      <Icon size={72} strokeWidth={1} />
                    </div>
                  )}
                  <span className="card-shade" aria-hidden="true" />
                  <span className="card-text">
                    <Icon size={20} aria-hidden="true" />
                    <strong>{t(`cat.${c.id}.t`)}</strong>
                    <small>{t(`cat.${c.id}.s`)}</small>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
