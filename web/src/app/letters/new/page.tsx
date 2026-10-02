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

