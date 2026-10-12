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

