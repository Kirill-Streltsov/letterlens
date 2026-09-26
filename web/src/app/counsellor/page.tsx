"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { InboxArt } from "@/components/Brand";
import { AppPage } from "@/components/Shell";
import { api, type CaseItem, type Me } from "@/lib/api";
import { daysUntil, deadlinePill, formatDate, LETTER_TYPES, relativeLabel } from "@/lib/format";

const FILTERS = [
  { value: "", label: "All open" },
  { value: "new", label: "New" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
];

function Inbox({ me }: { me: Me }) {
  const [status, setStatus] = useState("");
  const [cases, setCases] = useState<CaseItem[] | null>(null);
  const tenants = me.memberships.filter((m) => m.kind === "counselling");

  useEffect(() => {
    setCases(null);
    api.cases(status || undefined).then(setCases).catch(() => setCases([]));
  }, [status]);

  const sorted = [...(cases ?? [])].sort((a, b) => {
    const da = a.next_deadline?.due_date ?? "9999";
    const db = b.next_deadline?.due_date ?? "9999";
    return da.localeCompare(db);
  });

  return (
    <div className="stack" style={{ padding: "32px 0 64px" }}>
      <div className="row">
        <h1 style={{ margin: 0 }}>Case inbox</h1>
        <span className="faint">{tenants.map((t) => t.tenant_name).join(", ")}</span>
        <span className="spacer" />
        {tenants[0] && (
          <Link className="btn ghost small" href={`/counsellor/stats/?tenant=${tenants[0].tenant_id}`}>
            Statistics
          </Link>
        )}
      </div>
      <div className="row" role="tablist" aria-label="Filter cases">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            role="tab"
            aria-selected={status === f.value}
            className={`btn small ${status === f.value ? "" : "ghost"}`}
            onClick={() => setStatus(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>
      {cases === null && <div className="skeleton" style={{ height: 120 }} />}
      {cases?.length === 0 && (
        <div className="card empty">
          <InboxArt />
          <h2>No cases here</h2>
          <p className="muted">Clients share letters from the LetterLens app. Shared letters appear here with a summary.</p>
        </div>
      )}
      {sorted.length > 0 && (
        <div className="card" style={{ padding: 0, overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Next deadline</th>
                <th>Letter</th>
                <th>Client</th>
                <th>Status</th>
                <th>Shared</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => {
                const due = c.next_deadline?.due_date;
                const days = due ? daysUntil(due) : null;
                return (
                  <tr key={c.share_id}>
                    <td>
                      {due && days !== null ? (
                        <>
                          <span className={deadlinePill(days, c.next_deadline?.status ?? "")}>
                            {relativeLabel(days)}
                          </span>
                          <div className="faint">{formatDate(due)}</div>
                        </>
                      ) : (
                        <span className="faint">none found</span>
                      )}
                    </td>
                    <td>
                      <Link href={`/counsellor/case/?id=${c.share_id}`}>
                        <strong>{c.headline ?? "Letter"}</strong>
                      </Link>
                      <div className="faint">{LETTER_TYPES[c.letter_type ?? "other"]}</div>
                    </td>
                    <td>
                      {c.client_name ?? "Client"}
                      <div className="faint">language: {c.client_language}</div>
                    </td>
                    <td>
                      <span className="pill">{c.case_status.replace("_", " ")}</span>
                    </td>
                    <td className="faint">{formatDate(c.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function CounsellorPage() {
  return <AppPage>{(me) => <Inbox me={me} />}</AppPage>;
}
