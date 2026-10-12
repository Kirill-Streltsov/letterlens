import type { StatsRow } from "./api";

/** CSV for funding reports. Values are codes and counts only, so no escaping is needed. */
export function toCsv(rows: StatsRow[]): string {
  const head = "month,letter_type,language,cases,closed";
  return [head, ...rows.map((r) => [r.month, r.letter_type, r.language, r.cases, r.closed].join(","))].join("\n") + "\n";
}
