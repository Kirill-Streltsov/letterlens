/** iCalendar (RFC 5545) file for one deadline, with a reminder three days before. */

export interface IcsEvent {
  uid: string;
  date: string; // YYYY-MM-DD
  title: string;
  description: string;
}

function escape(text: string): string {
  return text.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
}

function fold(line: string): string {
  // Lines longer than 75 octets are folded (RFC 5545 3.1); characters are a safe approximation here.
  const parts: string[] = [];
  for (let i = 0; i < line.length; i += 73) parts.push((i ? " " : "") + line.slice(i, i + 73));
  return parts.join("\r\n");
}

export function buildIcs(event: IcsEvent, now: Date = new Date()): string {
  const day = event.date.replace(/-/g, "");
  const next = new Date(`${event.date}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  const end = next.toISOString().slice(0, 10).replace(/-/g, "");
  const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//LetterLens//Deadline//EN",
    "BEGIN:VEVENT",
    `UID:${event.uid}@letterlens`,
    `DTSTAMP:${stamp}`,
    `DTSTART;VALUE=DATE:${day}`,
    `DTEND;VALUE=DATE:${end}`,
    fold(`SUMMARY:${escape(event.title)}`),
    fold(`DESCRIPTION:${escape(event.description)}`),
    "BEGIN:VALARM",
    "TRIGGER:-P3D",
    "ACTION:DISPLAY",
    fold(`DESCRIPTION:${escape(event.title)}`),
    "END:VALARM",
    "END:VEVENT",
    "END:VCALENDAR",
    "",
  ].join("\r\n");
}

export function downloadIcs(event: IcsEvent): void {
  const blob = new Blob([buildIcs(event)], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `letterlens-${event.date}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}
