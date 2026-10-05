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

