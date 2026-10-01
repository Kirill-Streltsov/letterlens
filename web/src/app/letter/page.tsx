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
