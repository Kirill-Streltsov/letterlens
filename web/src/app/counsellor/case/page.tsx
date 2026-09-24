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

