"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AppPage } from "@/components/Shell";
import { api, ApiError, type Language, type LetterDocument, type Me } from "@/lib/api";
import { documentFromText, recognizeFiles } from "@/lib/ocr";

function NewLetter({ me }: { me: Me }) {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [language, setLanguage] = useState(me.preferred_language);
  const [doc, setDoc] = useState<LetterDocument | null>(null);
  const [paste, setPaste] = useState("");
  const [progress, setProgress] = useState<{ message: string; fraction: number } | null>(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef(crypto.randomUUID());

  useEffect(() => {
    api.languages().then(setLanguages).catch(() => undefined);
  }, []);

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    setDoc(null);
    try {
      const result = await recognizeFiles([...files], (message, fraction) => setProgress({ message, fraction }));
      setDoc(result);
      if (!result.lines.length) setError("No text was found. Try a sharper photo with more light.");
    } catch {
      setError("Text recognition failed. Try another photo, or paste the text below.");
    } finally {
      setProgress(null);
    }
  }

  async function submit() {
    const document = doc ?? (paste.trim() ? documentFromText(paste) : null);
    if (!document?.lines.length) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createLetter(document, language, idempotencyKey.current);
      router.push(`/letter/?id=${created.id}`);
    } catch (e) {
      setError(e instanceof ApiError && e.code === "quota_exceeded" ? `${e.message}. Upgrade in Settings.` : (e as Error).message);
      setSubmitting(false);
    }
  }

