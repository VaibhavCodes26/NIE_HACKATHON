// Decorative SVG motifs inspired by Karnataka heritage: temple gopuram, Gol Gumbaz dome,
// palace domes, and a Mysore-style border band. Pure SVG — no assets or dependencies.

export function HeritageSkyline({ className = '' }) {
  return (
    <svg
      className={className}
      viewBox="0 0 1440 320"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="rd-hill-a" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7a0d14" />
          <stop offset="1" stopColor="#5e0a10" />
        </linearGradient>
        <linearGradient id="rd-hill-b" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5a0a10" />
          <stop offset="1" stopColor="#3f070b" />
        </linearGradient>
      </defs>

      {/* far Western Ghats ridge */}
      <path
        d="M0 230 C120 170 220 210 340 175 C470 135 560 205 700 180 C830 156 930 200 1060 165 C1190 130 1320 190 1440 160 L1440 320 L0 320 Z"
        fill="url(#rd-hill-a)"
        opacity=".75"
      />

      {/* Gol Gumbaz-style great dome with corner minarets */}
      <g fill="#3f070b" opacity=".9">
        <rect x="190" y="205" width="170" height="115" />
        <path d="M205 205 C205 135 345 135 345 205 Z" />
        <rect x="270" y="130" width="10" height="14" />
        <rect x="180" y="185" width="16" height="135" />
        <rect x="354" y="185" width="16" height="135" />
        <path d="M178 185 h20 l-10 -16 z M352 185 h20 l-10 -16 z" />
      </g>

      {/* Dravidian gopuram (Virupaksha-inspired stepped tower) */}
      <g fill="#3f070b">
        <rect x="610" y="262" width="150" height="58" />
        <rect x="625" y="236" width="120" height="30" />
        <rect x="640" y="212" width="90" height="28" />
        <rect x="655" y="190" width="60" height="26" />
        <rect x="668" y="170" width="34" height="24" />
        <path d="M662 170 h46 l-23 -26 z" />
        <rect x="683" y="132" width="4" height="16" />
      </g>
      <g fill="#FFC928" opacity=".85">
        <rect x="676" y="276" width="18" height="44" rx="9" />
        <circle cx="685" cy="157" r="3" />
      </g>

      {/* Mysore Palace domes */}
      <g fill="#3f070b">
        <rect x="960" y="238" width="260" height="82" />
        <path d="M1010 238 C1010 196 1070 196 1070 238 Z" />
        <path d="M1110 238 C1110 186 1190 186 1190 238 Z" />
        <rect x="1148" y="168" width="4" height="22" />
        <circle cx="1150" cy="165" r="5" />
        <rect x="1038" y="190" width="3" height="14" />
      </g>
      <g fill="#FFC928" opacity=".8">
        {[985, 1015, 1045, 1075, 1105, 1135, 1165, 1195].map((x) => (
          <rect key={x} x={x} y="262" width="8" height="14" rx="4" />
        ))}
      </g>

      {/* foreground hills */}
      <path
        d="M0 275 C160 240 300 285 460 262 C620 240 760 290 920 266 C1080 242 1260 288 1440 258 L1440 320 L0 320 Z"
        fill="url(#rd-hill-b)"
      />

      {/* coconut palms on the coast side */}
      <g stroke="#2d0508" strokeWidth="5" strokeLinecap="round" fill="none">
        <path d="M520 320 C524 290 530 270 540 250" />
        <path d="M570 320 C568 295 566 278 560 262" />
      </g>
      <g stroke="#2d0508" strokeWidth="4" strokeLinecap="round" fill="none">
        <path d="M540 250 C525 244 512 248 505 256 M540 250 C552 240 566 240 574 246 M540 250 C536 236 542 226 552 222 M540 250 C528 238 520 232 508 232" />
        <path d="M560 262 C548 258 540 262 535 270 M560 262 C570 254 582 256 588 262 M560 262 C558 250 564 242 572 240" />
      </g>
    </svg>
  );
}

/** Decorative route line with heritage markers; sits on top of the hero. */
export function RouteLineDecor({ className = '' }) {
  const stops = [
    { x: 70, y: 96, label: 'Hampi' },
    { x: 250, y: 52, label: 'Badami' },
    { x: 440, y: 92, label: 'Mysuru' },
    { x: 640, y: 40, label: 'Gokarna' },
  ];
  return (
    <svg className={className} viewBox="0 0 720 130" aria-hidden="true" focusable="false">
      <path
        className="rd-routeline"
        d="M70 96 C140 120 190 30 250 52 C320 78 370 120 440 92 C510 64 570 20 640 40"
        fill="none"
        stroke="#FFC928"
        strokeWidth="2.5"
        strokeDasharray="3 9"
        strokeLinecap="round"
      />
      {stops.map((s, i) => (
        <g key={s.label} className="rd-routepin" style={{ animationDelay: `${0.6 + i * 0.25}s` }}>
          <circle cx={s.x} cy={s.y} r="11" fill="#B5121B" stroke="#FFC928" strokeWidth="2.5" />
          <path
            d={`M${s.x - 4} ${s.y + 3} L${s.x} ${s.y - 5} L${s.x + 4} ${s.y + 3} Z`}
            fill="#FFC928"
          />
          <text
            x={s.x}
            y={s.y + 30}
            textAnchor="middle"
            fontSize="12"
            fontWeight="600"
            fill="#FFF9EC"
            style={{ letterSpacing: '.06em' }}
          >
            {s.label.toUpperCase()}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** Repeating diamond-and-lotus border band used as a heritage divider. */
export function HeritageBorder({ className = '' }) {
  return (
    <svg className={className} width="100%" height="18" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="rd-border" width="36" height="18" patternUnits="userSpaceOnUse">
          <rect width="36" height="18" fill="#B5121B" />
          <path d="M18 2 L28 9 L18 16 L8 9 Z" fill="#FFC928" />
          <path d="M18 6 L23 9 L18 12 L13 9 Z" fill="#B5121B" />
          <circle cx="0" cy="9" r="2" fill="#FFC928" />
          <circle cx="36" cy="9" r="2" fill="#FFC928" />
        </pattern>
      </defs>
      <rect width="100%" height="18" fill="url(#rd-border)" />
    </svg>
  );
}

/** Faint geometric lattice for card backgrounds. */
export function LatticeBackdrop({ className = '' }) {
  return (
    <svg className={className} width="100%" height="100%" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="rd-lattice" width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M24 4 L44 24 L24 44 L4 24 Z" fill="none" stroke="#B5121B" strokeWidth="1" />
          <circle cx="24" cy="24" r="3" fill="none" stroke="#F4B400" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#rd-lattice)" />
    </svg>
  );
}