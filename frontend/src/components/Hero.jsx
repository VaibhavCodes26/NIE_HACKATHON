import { useState } from 'react';
import { ChevronLeft, ChevronRight, Landmark, Utensils, Mountain, Drama, MapPin, ArrowRight } from 'lucide-react';
import Img from './Img';
import { DESTINATIONS, commonsImg } from '../data/destinations';
import { useI18n } from '../i18n';

const CHIPS = [['temples', Landmark], ['food', Utensils], ['hills', Mountain], ['festivals', Drama]];
const N = DESTINATIONS.length;
const SLIDES = DESTINATIONS.map((d) => ({ ...d, img: commonsImg(d.file, 1400), thumb: commonsImg(d.file, 240) }));

export default function Hero({ onPlan, onFood, onCategory, onDestination }) {
  const { t } = useI18n();
  const [idx, setIdx] = useState(0);
  const d = SLIDES[idx];
  const go = (i) => setIdx((i + N) % N);

  const onKey = (e) => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); go(idx - 1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); go(idx + 1); }
  };

  return (
    <section id="home" className="hero">
      <div className="container hero-grid">
        <div className="hero-copy">
          <span className="accent" aria-hidden="true"><i /><i /><i /></span>
          <h1 className="hero-kn" lang="kn">ನಮ್ಮ ಕರ್ನಾಟಕ, ನಮ್ಮ ಹೆಮ್ಮೆ</h1>
          <p className="hero-en">{t('hero.en')}</p>
          <p className="hero-sub">{t('hero.sub')}</p>
          <div className="cta-row">
            <button className="btn btn-primary" onClick={onPlan}>{t('cta.plan')} <ArrowRight size={18} aria-hidden="true" /></button>
            <button className="btn btn-ghost" onClick={onFood}>{t('cta.food')}</button>
          </div>
          <ul className="chips">
            {CHIPS.map(([id, Icon]) => (
              <li key={id}>
                <button onClick={() => (id === 'food' ? onFood() : onCategory(id))}>
                  <Icon size={26} strokeWidth={1.5} aria-hidden="true" />
                  <span>{t(`chip.${id}`)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="hero-media">
          <div className="carousel" role="group" aria-roledescription="carousel" aria-label={t('car.label')} tabIndex={0} onKeyDown={onKey}>
            {SLIDES.map((s, i) => (
              <figure key={s.id} className={`slide ${i === idx ? 'on' : ''}`} aria-hidden={i !== idx}>
                <Img src={s.img} alt={s.alt} eager={i === 0} className="slide-img" label={s.name} />
                <figcaption><MapPin size={16} aria-hidden="true" /> {s.overlay} <em lang="kn">{s.kn}</em></figcaption>
              </figure>
            ))}
            <span className="counter" aria-hidden="true">{String(idx + 1).padStart(2, '0')} / {String(N).padStart(2, '0')}</span>
            <button className="arrow left" aria-label={t('car.prev')} onClick={() => go(idx - 1)}><ChevronLeft /></button>
            <button className="arrow right" aria-label={t('car.next')} onClick={() => go(idx + 1)}><ChevronRight /></button>
          </div>
          <div className="dots">
            {SLIDES.map((s, i) => (
              <button key={s.id} className={i === idx ? 'on' : ''} aria-label={`${t('car.goto')}: ${s.name} (${i + 1}/${N})`}
                aria-current={i === idx ? 'true' : undefined} onClick={() => go(i)}><i /></button>
            ))}
          </div>
        </div>
      </div>

      <div className="container">
        <article className="story" aria-live="polite" key={d.id}>
          <Img src={d.thumb} alt={d.alt} className="story-thumb" label="" />
          <span className="story-div" aria-hidden="true" />
          <div className="story-text">
            <h2>{d.heading}</h2>
            <p>{d.description}</p>
            <span className="story-loc"><MapPin size={15} aria-hidden="true" /> {d.location}</span>
          </div>
          <button className="story-more" onClick={() => onDestination(d.id)}>{t('story.more')} <ArrowRight size={18} aria-hidden="true" /></button>
        </article>
      </div>
    </section>
  );
}
