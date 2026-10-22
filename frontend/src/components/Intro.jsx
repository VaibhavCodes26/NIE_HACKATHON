import { useEffect, useState } from 'react';
import { KA_PATH, KA_W, KA_H } from '../data/karnataka';
import { Wordmark } from './Logo';
import { useI18n } from '../i18n';

// ~3.9s: outline draws (0.2–2.0s) -> gold fill + wordmark (1.7–2.6s) -> hold -> fade out (3.3s).
export default function Intro({ onDone }) {
  const { t } = useI18n();
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const a = setTimeout(() => setLeaving(true), 3300);
    const b = setTimeout(onDone, 3900);
    const onKey = (e) => e.key === 'Escape' && onDone();
    window.addEventListener('keydown', onKey);
    return () => { clearTimeout(a); clearTimeout(b); window.removeEventListener('keydown', onKey); };
  }, [onDone]);

  return (
    <div className={`intro ${leaving ? 'leaving' : ''}`} role="dialog" aria-label="NammaPrayana introduction">
      <div className="intro-comp">
        <svg className="intro-map" viewBox={`-10 -10 ${KA_W + 20} ${KA_H + 20}`} aria-hidden="true" focusable="false"
             style={{ aspectRatio: `${KA_W + 20} / ${KA_H + 20}` }}>
          <path className="ink-fill" d={KA_PATH} />
          <path className="ink-gold" d={KA_PATH} pathLength="1" transform="translate(5 5)" />
          <path className="ink" d={KA_PATH} pathLength="1" />
        </svg>
        <div className="intro-word">
          <Wordmark className="wordmark-xl" />
          <p className="intro-tag">{t('tagline')}</p>
          <p className="intro-kn" lang="kn">ನಮ್ಮ ಪ್ರಯಾಣ</p>
        </div>
      </div>
      <button className="intro-skip" onClick={onDone}>{t('skip')} →</button>
    </div>
  );
}
