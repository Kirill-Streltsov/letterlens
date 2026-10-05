/** Logo and illustrations, drawn inline so they work offline and under a strict CSP. */

export function Logo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <rect x="4" y="10" width="32" height="24" rx="3" fill="var(--card)" stroke="var(--ink)" strokeWidth="2.5" />
      <path d="M5 12l15 11 15-11" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinejoin="round" />
      <circle cx="31" cy="29" r="9" fill="var(--marker)" fillOpacity="0.85" stroke="var(--ink)" strokeWidth="2.5" />
      <path d="M37.5 35.5L44 42" stroke="var(--ink)" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  );
}

export function EnvelopeArt() {
  return (
    <svg viewBox="0 0 240 170" aria-hidden="true">
      <rect x="18" y="30" width="170" height="118" rx="10" fill="var(--card)" stroke="var(--line)" strokeWidth="3" />
      <path d="M22 36l81 58 81-58" fill="none" stroke="var(--ink-faint)" strokeWidth="3" />
      <rect x="44" y="12" width="120" height="70" rx="6" fill="var(--card)" stroke="var(--ink-soft)" strokeWidth="2" transform="rotate(-6 104 47)" />
      <rect x="58" y="28" width="70" height="8" rx="4" fill="var(--marker)" transform="rotate(-6 104 47)" />
      <rect x="58" y="44" width="88" height="5" rx="2.5" fill="var(--line)" transform="rotate(-6 104 47)" />
      <rect x="58" y="56" width="60" height="5" rx="2.5" fill="var(--line)" transform="rotate(-6 104 47)" />
      <circle cx="178" cy="120" r="30" fill="var(--marker)" fillOpacity="0.7" stroke="var(--ink)" strokeWidth="4" />
      <path d="M200 142l22 22" stroke="var(--ink)" strokeWidth="7" strokeLinecap="round" />
    </svg>
  );
}

export function InboxArt() {
  return (
    <svg viewBox="0 0 240 170" aria-hidden="true">
      <path d="M30 70l30-44h120l30 44v70a8 8 0 01-8 8H38a8 8 0 01-8-8z" fill="var(--card)" stroke="var(--line)" strokeWidth="3" />
      <path d="M30 70h55l10 20h50l10-20h55" fill="none" stroke="var(--ink-faint)" strokeWidth="3" />
      <rect x="80" y="40" width="80" height="8" rx="4" fill="var(--marker)" />
      <rect x="92" y="56" width="56" height="6" rx="3" fill="var(--line)" />
    </svg>
  );
}
