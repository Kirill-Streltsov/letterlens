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

  return (
    <div className="workspace">
      <OriginalPanel lines={letter.lines} highlight={highlight} />
      <div className="stack">
        {letter.degraded && (
          <p className="notice" role="status">
            The assistant was not fully available. This result uses simple rules; please check everything carefully.
          </p>
        )}
        {explanation && (
          <section className="card" dir={rtl ? "rtl" : "ltr"} lang={explanation.language}>
            <div className="row">
              <span className="pill">{LETTER_TYPES[letter.classification?.letter_type ?? "other"]}</span>
              {facts?.sender.value && <span className="faint">{facts.sender.value}</span>}
            </div>
            <h1 style={{ fontSize: "1.6rem", marginTop: 12 }}>{explanation.headline}</h1>
            <p className="muted">{explanation.letter_kind}</p>
            <ul className="summary">
              {explanation.summary.map((s, i) => (
                <li
                  key={i}
                  tabIndex={0}
                  onMouseEnter={() => focus(s.line_ids)}
                  onFocus={() => focus(s.line_ids)}
                  onMouseLeave={() => setHover([])}
                >
                  {s.text}
                </li>
              ))}
            </ul>
          </section>
        )}

        {facts && facts.deadlines.length > 0 && (
          <section aria-label="Deadlines">
            <h2>Deadlines</h2>
            <div className="deadlines">
              {facts.deadlines.map((d) => (
                <div key={d.id} onMouseEnter={() => focus(d.line_ids)} onMouseLeave={() => setHover([])}>
                  <DeadlineCard d={d} letterId={letter.id} label={explanation?.deadline_labels[d.id] ?? d.description} />
                </div>
              ))}
            </div>
          </section>
        )}

        {facts && facts.amounts.length > 0 && (
          <section className="card" aria-label="Amounts">
            <h2>Amounts</h2>
            {facts.amounts.map((a) => (
              <div className="amount" key={a.id} onMouseEnter={() => focus(a.line_ids)} onMouseLeave={() => setHover([])}>
                <div>
                  <div>{explanation?.amount_labels[a.id] ?? a.description}</div>
                  <div className="faint">
                    {DIRECTION[a.direction]} ·{" "}
                    {a.status === "verified" ? "found in the letter" : <span style={{ color: "var(--check)" }}>please check</span>}
                  </div>
                </div>
                <div className="value">{money(a.value, a.currency)}</div>
              </div>
            ))}
          </section>
        )}

