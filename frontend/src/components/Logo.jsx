import { KA_PATH, KA_W, KA_H } from '../data/karnataka';
export const KaMark = ({ size = 34 }) => (
  <svg width={size * ((KA_W + 20) / (KA_H + 20))} height={size} viewBox={`-10 -10 ${KA_W + 20} ${KA_H + 20}`} aria-hidden="true" focusable="false">
    <path d={KA_PATH} fill="var(--gold)" stroke="var(--red)" strokeWidth="14" strokeLinejoin="round" />
  </svg>
);
export const Wordmark = ({ className = '' }) => (
  <span className={`wordmark ${className}`}>
    <span className="w-red">NAMMA</span><span className="w-gold">PRAYANA</span>
  </span>
);
