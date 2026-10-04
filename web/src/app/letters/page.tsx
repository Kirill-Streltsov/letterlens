"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EnvelopeArt } from "@/components/Brand";
import { AppPage } from "@/components/Shell";
import { api, type LetterListItem, type Me } from "@/lib/api";
import { daysUntil, deadlinePill, formatDate, LETTER_TYPES, relativeLabel } from "@/lib/format";

function Letters({ me }: { me: Me }) {
  const [letters, setLetters] = useState<LetterListItem[] | null>(null);

  useEffect(() => {
    api.letters().then(setLetters).catch(() => setLetters([]));
  }, []);

  const left = me.letters_limit === null ? null : Math.max(me.letters_limit - me.letters_this_month, 0);

  return (
    <div className="stack" style={{ padding: "32px 0 64px" }}>
      <div className="row">
        <h1 style={{ margin: 0 }}>My letters</h1>
        <span className="spacer" />
        {left !== null && <span className="faint">{left} of {me.letters_limit} free letters left this month</span>}
        <Link className="btn" href="/letters/new/">
          New letter
        </Link>
      </div>
      {letters === null && <div className="skeleton" style={{ height: 80 }} />}
      {letters?.length === 0 && (
        <div className="card empty">
          <EnvelopeArt />
          <h2>No letters yet</h2>
          <p className="muted">Take a photo of a letter or upload a PDF. Text recognition runs on your device.</p>
          <Link className="btn" href="/letters/new/">
            Add your first letter
          </Link>
        </div>
      )}
      <div className="list">
        {letters?.map((l) => {
          const days = l.next_deadline?.due_date ? daysUntil(l.next_deadline.due_date) : null;
          return (
            <Link key={l.id} href={`/letter/?id=${l.id}`} className="card list-item">
              <div>
                <div className="row">
                  <span className="pill">{LETTER_TYPES[l.letter_type ?? "other"] ?? "Letter"}</span>
                  {l.status !== "ready" && <span className="pill check">{l.status}</span>}
                  {l.shared && <span className="pill ok">shared with counselling</span>}
