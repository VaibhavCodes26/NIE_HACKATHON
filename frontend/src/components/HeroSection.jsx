import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { HeritageSkyline, RouteLineDecor } from './Motifs';
import { HERO_IMAGE, HERO_QUOTES, SHOWCASE } from '../data/locations';

export default function HeroSection() {
  const [quoteIdx, setQuoteIdx] = useState(0);
  const [imgOk, setImgOk] = useState(true);

  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return undefined;
    const t = setInterval(() => setQuoteIdx((i) => (i + 1) % HERO_QUOTES.length), 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="rd-hero">
      {imgOk && (
        <img
          className="rd-hero__photo"
          src={HERO_IMAGE}
          alt=""
          loading="eager"
          onError={() => setImgOk(false)}
        />
      )}
      <div className="rd-hero__wash" />
      <div className="rd-hero__sun" aria-hidden="true" />
      <HeritageSkyline className="rd-hero__skyline" />

      <div className="rd-container rd-hero__inner">
        <div className="rd-hero__copy">
          <p className="rd-eyebrow rd-rise" style={{ '--d': '0s' }}>
            <Sparkles size={14} aria-hidden="true" /> DISCOVER KARNATAKA
          </p>
          <h1 className="rd-hero__title rd-rise" style={{ '--d': '.08s' }}>
            Every Journey Tells a <span>Karnataka Story</span>
          </h1>
          <p className="rd-hero__lead rd-rise" style={{ '--d': '.16s' }}>
            From the timeless grandeur of Hampi and Mysuru&rsquo;s royal heritage to the mist-covered
            Western Ghats and the golden shores of the Arabian Sea, discover Karnataka one
            unforgettable journey at a time.
          </p>

          <div className="rd-kannada rd-rise" style={{ '--d': '.24s' }}>
            <p className="rd-kannada__text" lang="kn">
              ಬನ್ನಿ, ಕರ್ನಾಟಕವನ್ನು ಅನ್ವೇಷಿಸೋಣ
            </p>
            <p className="rd-kannada__en">&ldquo;Come, let&rsquo;s explore Karnataka.&rdquo;</p>
          </div>

          <p className="rd-quote rd-rise" style={{ '--d': '.32s' }} aria-live="polite">
            <span key={quoteIdx} className="rd-quote__text">
              {HERO_QUOTES[quoteIdx]}
            </span>
          </p>
        </div>

        <aside className="rd-hero__aside rd-rise" style={{ '--d': '.3s' }} aria-hidden="true">
          <RouteLineDecor className="rd-hero__route" />
          <ul className="rd-chips">
            {SHOWCASE.map((s) => (
              <li key={s.name}>
                <strong>{s.name}</strong>
                <span>{s.tag}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </header>
  );
}