/** Display helpers. Dates are shown with the weekday because deadlines are about days. */

export function formatDate(iso: string | null | undefined, locale = "en-GB"): string {
  if (!iso) return "—";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00Z`);
  return d.toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

export function daysUntil(iso: string, today: Date = new Date()): number {
  const target = Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((target - now) / 86_400_000);
}

export function urgency(days: number): "past" | "urgent" | "soon" | "later" {
  if (days < 0) return "past";
  if (days <= 3) return "urgent";
  if (days <= 14) return "soon";
  return "later";
}

export function relativeLabel(days: number): string {
  if (days < 0) return `${-days} day${days === -1 ? "" : "s"} ago`;
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

