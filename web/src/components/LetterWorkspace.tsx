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

