"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { LetterWorkspace } from "@/components/LetterWorkspace";
import { AppPage } from "@/components/Shell";
import {
  api,
  type CounsellingService,
  type Language,
  type LetterView,
  type Me,
  type Message,
  type QuestionResponse,
} from "@/lib/api";

function QuestionBox({ letterId, language }: { letterId: string; language: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<QuestionResponse | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <section className="card stack">
      <h2>Ask about this letter</h2>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim().length < 3) return;
          setBusy(true);
          api
            .ask(letterId, question, language)
            .then(setAnswer)
            .catch((err: Error) =>
              setAnswer({ answer: err.message, refused: true, reason: null, handover_suggested: false, line_ids: [], citations: [] }),
            )
            .finally(() => setBusy(false));
        }}
      >
        <input
          aria-label="Your question"
          placeholder="For example: What does “Bekanntgabe” mean?"
          value={question}
          maxLength={600}
          onChange={(e) => setQuestion(e.target.value)}
          style={{ flex: 1, width: "auto" }}
        />
        <button className="btn" disabled={busy}>
          {busy ? "…" : "Ask"}
        </button>
      </form>
      {answer && (
        <div className={answer.refused ? "notice" : "notice info"} aria-live="polite">
          {answer.answer ?? "I could not check this answer against the letter. Please ask a counsellor."}
          {answer.citations.length > 0 && (
            <div className="faint" style={{ marginTop: 6 }}>
              Sources: {answer.citations.map((c) => c.title).join("; ")}
            </div>
          )}
        </div>
      )}
      <p className="faint">LetterLens gives general information. It does not tell you what to decide in your case.</p>
    </section>
  );
}

function SharePanel({ letter, onChange }: { letter: LetterView; onChange: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [services, setServices] = useState<CounsellingService[]>([]);
  const [tenant, setTenant] = useState("");
  const [agree, setAgree] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const active = letter.shares.find((s) => !s.revoked);

  useEffect(() => {
    if (active) api.messages(active.id).then(setMessages).catch(() => undefined);
  }, [active]);

  return (
    <section className="card stack">
      <h2>Talk to a counsellor</h2>
      {active ? (
        <>
          <p>
            Shared with <strong>{active.tenant_name}</strong> until {active.expires_at.slice(0, 10)}. Case status:{" "}
            <span className="pill">{active.case_status.replace("_", " ")}</span>
          </p>
          <div className="thread" aria-live="polite">
            {messages.length === 0 && <p className="faint">No messages yet. The counsellor will answer here.</p>}
            {messages.map((m) => (
              <div key={m.id} className={`bubble${m.author_role === "client" ? " mine" : ""}`}>
                {m.text}
                {m.original_text && <div className="orig">Original: {m.original_text}</div>}
              </div>
            ))}
          </div>
          <form
            className="row"
            onSubmit={(e) => {
