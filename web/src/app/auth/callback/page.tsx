"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { completeSignIn } from "@/lib/auth";

function Callback() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const code = params.get("code");
    if (!code) {
      setError(params.get("error_description") ?? "Sign-in was cancelled.");
      return;
    }
    completeSignIn(code)
      .then(() => router.replace("/letters/"))
      .catch((e: Error) => setError(e.message));
  }, [params, router]);

