"use client";

import { useEffect, useState } from "react";

import { AppPage } from "@/components/Shell";
import { api, type Language, type Me } from "@/lib/api";
import { signOut } from "@/lib/auth";

function Settings({ me }: { me: Me }) {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [name, setName] = useState(me.display_name ?? "");
  const [language, setLanguage] = useState(me.preferred_language);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.languages().then(setLanguages).catch(() => undefined);
  }, []);

  const flash = (text: string) => setMessage(text);

  return (
    <div className="stack" style={{ padding: "32px 0 64px", maxWidth: 680 }}>
      <h1>Settings</h1>
      {message && <p className="notice info" role="status">{message}</p>}

