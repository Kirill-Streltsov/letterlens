"use client";

import { useMemo, useState } from "react";

import type { LetterView, Schemas } from "@/lib/api";
import { daysUntil, DIRECTION, formatDate, LETTER_TYPES, money, relativeLabel, urgency } from "@/lib/format";
import { downloadIcs } from "@/lib/ics";

type Explanation = Schemas["Explanation"];

export function OriginalPanel({ lines, highlight }: { lines: LetterView["lines"]; highlight: Set<string> }) {
  return (
    <section className="card original" aria-label="Original letter" lang="de">
      <h2 style={{ fontSize: "1rem" }} className="muted">
        Original letter
      </h2>
      {lines.map((line, i) => {
        const id = `p${line.page}-l${line.index}`;
        const pageBreak = i > 0 && lines[i - 1]?.page !== line.page;
        return (
          <div key={id}>
            {pageBreak && <div className="page-break" aria-hidden="true" />}
            <div id={id} className={`line${highlight.has(id) ? " hl" : ""}`}>
              {line.text}
            </div>
          </div>
        );
      })}
    </section>
  );
}

function DeadlineCard({ d, label, letterId }: { d: Schemas["VerifiedDeadline"]; label: string; letterId: string }) {
  const days = d.due_date ? daysUntil(d.due_date) : null;
  const level = days === null ? null : urgency(days);
  return (
    <article className={`card tight deadline ${d.status}`}>
      <div className="row">
        {d.status === "verified" ? (
          <span className="pill ok">Found in the letter</span>
        ) : (
          <span className="pill check">Please check</span>
        )}
        {level === "urgent" && <span className="pill urgent">{relativeLabel(days!)}</span>}
      </div>
      <div className="date" style={{ marginTop: 8 }}>
        {d.due_date ? formatDate(d.due_date) : "Date unknown"}
      </div>
      {days !== null && level !== "urgent" && <div className="faint">{relativeLabel(days)}</div>}
      <p style={{ marginTop: 8 }}>{label}</p>
      {d.note && <p className="faint">{d.note}</p>}
      {d.rule && (
        <details className="faint">
          <summary>How this date was estimated</summary>
          {d.rule}
        </details>
      )}
      {d.due_date && (
        <button
          className="btn ghost small"
          onClick={() =>
            downloadIcs({
              uid: `${letterId}-${d.id}`,
              date: d.due_date!,
              title: `Deadline: ${label}`,
              description: `${d.status === "verified" ? "" : "PLEASE CHECK THIS DATE IN THE LETTER. "}${d.source_text ?? ""}`,
            })
          }
        >
          Add to calendar
        </button>
      )}
    </article>
  );
}

export function LetterWorkspace({
  letter,
  explanation,
  side,
}: {
  letter: LetterView;
  explanation: Explanation | null;
  side?: React.ReactNode;
}) {
  const [hover, setHover] = useState<string[]>([]);
  const highlight = useMemo(() => new Set(hover), [hover]);
  const facts = letter.facts;
  const rtl = explanation?.language === "ar";

  const focus = (ids: string[]) => {
    setHover(ids);
    const first = ids[0];
    if (first) document.getElementById(first)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  };

