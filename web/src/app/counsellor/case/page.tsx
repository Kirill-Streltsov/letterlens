"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { LetterWorkspace } from "@/components/LetterWorkspace";
import { AppPage } from "@/components/Shell";
import { api, type CaseDetail, type Message } from "@/lib/api";

function CaseView() {
  const id = useSearchParams().get("id") ?? "";
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [view, setView] = useState<"de" | "client">("de");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.caseDetail(id).then(setDetail).catch((e: Error) => setError(e.message));
    api.messages(id).then(setMessages).catch(() => undefined);
  }, [id]);

  useEffect(load, [load]);

  if (error) return <p className="notice" style={{ marginTop: 32 }}>{error}</p>;
  if (!detail) return <div className="skeleton" style={{ height: 240, marginTop: 32 }} />;

  const explanation = view === "de" ? (detail.explanation_de ?? detail.letter.explanation) : detail.letter.explanation;

  const side = (
    <section className="card stack">
      <h2>Messages with {detail.client_name ?? "the client"}</h2>
      <div className="thread" aria-live="polite">
        {messages.length === 0 && <p className="faint">No messages yet.</p>}
        {messages.map((m) => (
          <div key={m.id} className={`bubble${m.author_role === "counsellor" ? " mine" : ""}`}>
            {m.text}
            {m.original_text && <div className="orig">Original ({detail.client_language}): {m.original_text}</div>}
          </div>
        ))}
      </div>
      <label htmlFor="reply">Reply in German. The client receives it in {detail.client_language}.</label>
      <textarea id="reply" value={text} onChange={(e) => setText(e.target.value)} style={{ minHeight: 90 }} lang="de" />
      {preview && (
        <p className="notice info" lang={detail.client_language}>
          Translation preview: {preview}
        </p>
      )}
      <div className="row">
        <button
          className="btn ghost small"
          disabled={!text.trim()}
          onClick={() => api.translate(text, detail.client_language).then((r) => setPreview(r.translation))}
        >
          Preview translation
        </button>
        <button
          className="btn small"
          disabled={!text.trim()}
          onClick={() =>
            api.sendMessage(id, text).then((m) => {
              setMessages((old) => [...old, m]);
              setText("");
              setPreview(null);
            })
          }
        >
          Send
        </button>
      </div>
    </section>
  );

  return (
    <>
      <div className="row" style={{ paddingTop: 24 }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Case: {detail.client_name ?? "client"}</h1>
        <span className="spacer" />
        <div className="row" role="tablist" aria-label="Summary language">
          <button className={`btn small ${view === "de" ? "" : "ghost"}`} onClick={() => setView("de")} role="tab" aria-selected={view === "de"}>
            Deutsch
          </button>
          <button className={`btn small ${view === "client" ? "" : "ghost"}`} onClick={() => setView("client")} role="tab" aria-selected={view === "client"}>
            Client view ({detail.client_language})
          </button>
        </div>
        <select
          aria-label="Case status"
          value={detail.case_status}
          style={{ width: "auto" }}
          onChange={(e) =>
            api.updateCase(id, { case_status: e.target.value as "new" | "in_progress" | "closed" }).then(load)
          }
        >
          <option value="new">New</option>
          <option value="in_progress">In progress</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <LetterWorkspace letter={detail.letter} explanation={explanation ?? null} side={side} />
    </>
  );
}

export default function CasePage() {
  return (
    <AppPage>
      {() => (
        <Suspense>
          <CaseView />
        </Suspense>
      )}
    </AppPage>
  );
}
