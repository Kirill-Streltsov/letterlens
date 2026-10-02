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
              e.preventDefault();
              if (!text.trim()) return;
              api.sendMessage(active.id, text).then((m) => {
                setMessages((old) => [...old, m]);
                setText("");
              });
            }}
          >
            <input aria-label="Message" value={text} onChange={(e) => setText(e.target.value)} style={{ flex: 1, width: "auto" }} />
            <button className="btn small">Send</button>
          </form>
          <button className="btn danger small" onClick={() => api.revokeShare(active.id).then(onChange)}>
            Stop sharing
          </button>
        </>
      ) : (
        <>
          <p className="muted">
            A free counselling service can look at your letter and help with your case. You decide if and with whom to
            share it.
          </p>
          <button
            className="btn ghost"
            onClick={() => {
              api.services().then(setServices);
              dialog.current?.showModal();
            }}
          >
            Share with a counselling service
          </button>
        </>
      )}
      <dialog ref={dialog} aria-labelledby="share-title">
        <form
          method="dialog"
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            if (!tenant || !agree) return;
            api.share(letter.id, tenant).then(() => {
              dialog.current?.close();
              onChange();
            });
          }}
        >
          <h2 id="share-title">Share this letter</h2>
          <label htmlFor="service">Counselling service</label>
          <select id="service" value={tenant} onChange={(e) => setTenant(e.target.value)} required>
            <option value="">Choose…</option>
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
                {s.city ? ` (${s.city})` : ""}
              </option>
            ))}
          </select>
          <label style={{ display: "flex", gap: 10, fontWeight: 400 }}>
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} style={{ width: "auto" }} />
            <span>
              I agree that this counselling service can see the text of this letter, the summary and my messages for 30
              days. I can stop sharing at any time. (Consent version share-consent-v1)
            </span>
          </label>
          <div className="row">
            <button className="btn" disabled={!tenant || !agree}>
              Share
            </button>
            <button type="button" className="btn ghost" onClick={() => dialog.current?.close()}>
              Cancel
            </button>
          </div>
        </form>
      </dialog>
    </section>
  );
}

function Letter({ me }: { me: Me }) {
  const id = useSearchParams().get("id") ?? "";
  const router = useRouter();
  const [language, setLanguage] = useState(me.preferred_language);
  const [letter, setLetter] = useState<LetterView | null>(null);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.letter(id, language).then(setLetter).catch((e: Error) => setError(e.message));
  }, [id, language]);

  useEffect(() => {
    load();
    api.languages().then(setLanguages).catch(() => undefined);
  }, [load]);

  useEffect(() => {
    if (!letter || letter.status === "ready" || letter.status === "failed") return;
    const timer = setTimeout(load, 1500);
    return () => clearTimeout(timer);
  }, [letter, load]);

  if (error) return <p className="notice" style={{ marginTop: 32 }}>{error}</p>;
  if (!letter) return <div className="skeleton" style={{ height: 240, marginTop: 32 }} />;

  const switchLanguage = (code: string) => {
    setLanguage(code);
    if (!letter.explanation_languages.includes(code)) {
      api.explain(letter.id, code).then(() => setLetter({ ...letter, status: "processing" }));
    }
  };

  const explanation = letter.explanation;
  const processing = letter.status === "received" || letter.status === "processing";
  const missing = letter.status === "ready" && !letter.explanation_languages.includes(language);
  const languageName = languages.find((l) => l.code === language)?.native_name ?? language;

  return (
    <>
      <div className="row" style={{ paddingTop: 24 }}>
        <label htmlFor="lang" className="sr-only">
          Language
        </label>
        <select id="lang" value={language} onChange={(e) => switchLanguage(e.target.value)} style={{ width: "auto" }}>
          {languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.native_name}
              {l.status === "experimental" ? " · beta" : ""}
            </option>
          ))}
        </select>
        {processing && <span className="pill check" aria-live="polite">Reading the letter…</span>}
        {letter.status === "failed" && <span className="pill urgent">Processing failed</span>}
        {missing && (
          <button className="btn small" onClick={() => switchLanguage(language)}>
            Explain in {languageName}
          </button>
        )}
        <span className="spacer" />
        <button
          className="btn danger small"
          onClick={() => {
            if (confirm("Delete this letter and its results? This cannot be undone.")) {
              api.deleteLetter(letter.id).then(() => router.push("/letters/"));
            }
          }}
        >
          Delete letter
        </button>
      </div>
      <LetterWorkspace
        letter={letter}
        explanation={explanation ?? null}
        side={
          letter.status === "ready" ? (
            <>
              <QuestionBox letterId={letter.id} language={language} />
              <SharePanel letter={letter} onChange={load} />
            </>
          ) : null
        }
      />
    </>
  );
}

export default function LetterPage() {
  return (
    <AppPage>
      {(me) => (
        <Suspense>
          <Letter me={me} />
        </Suspense>
      )}
    </AppPage>
  );
}
