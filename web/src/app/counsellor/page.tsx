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
