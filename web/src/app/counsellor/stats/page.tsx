"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AppPage } from "@/components/Shell";
import { api, type StatsRow } from "@/lib/api";
import { toCsv } from "@/lib/csv";
import { LETTER_TYPES } from "@/lib/format";

function Stats() {
  const tenant = useSearchParams().get("tenant") ?? "";
  const [rows, setRows] = useState<StatsRow[] | null>(null);
  const [invite, setInvite] = useState<string | null>(null);

  useEffect(() => {
    api.stats(tenant).then(setRows).catch(() => setRows([]));
  }, [tenant]);

  const total = rows?.reduce((s, r) => s + r.cases, 0) ?? 0;

  return (
    <div className="stack" style={{ padding: "32px 0 64px" }}>
      <div className="row">
        <h1 style={{ margin: 0 }}>Statistics for funding reports</h1>
        <span className="spacer" />
        <button
          className="btn ghost small"
          disabled={!rows?.length}
          onClick={() => {
            const url = URL.createObjectURL(new Blob([toCsv(rows ?? [])], { type: "text/csv" }));
            const a = document.createElement("a");
            a.href = url;
            a.download = "letterlens-cases.csv";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          Download CSV
        </button>
      </div>
      <p className="muted">Counts only. No names, no letter content. {total} cases in the last 12 months.</p>
      <div className="card" style={{ padding: 0, overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Month</th>
              <th>Letter type</th>
              <th>Client language</th>
              <th>Cases</th>
              <th>Closed</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={`${r.month}-${r.letter_type}-${r.language}`}>
                <td>{r.month.slice(0, 7)}</td>
                <td>{LETTER_TYPES[r.letter_type] ?? r.letter_type}</td>
                <td>{r.language}</td>
                <td>{r.cases}</td>
                <td>{r.closed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <section className="card stack" style={{ maxWidth: 520 }}>
