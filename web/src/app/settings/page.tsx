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

      <section className="card stack">
        <h2>Profile</h2>
        <label htmlFor="name">Name shown to counsellors (optional)</label>
        <input id="name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
        <label htmlFor="lang">Preferred language</label>
        <select id="lang" value={language} onChange={(e) => setLanguage(e.target.value)}>
          {languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.native_name} ({l.name})
            </option>
          ))}
        </select>
        <div>
          <button
            className="btn small"
            onClick={() => api.updateMe({ display_name: name || null, preferred_language: language }).then(() => flash("Saved."))}
          >
            Save
          </button>
        </div>
      </section>

      <section className="card stack">
        <h2>Plan</h2>
        <p>
          You use <strong>LetterLens {me.plan === "plus" ? "Plus" : "Free"}</strong>
          {me.letters_limit !== null && ` (${me.letters_this_month} of ${me.letters_limit} letters this month)`}.
        </p>
        {me.plan === "free" && (
          <div>
            <button
              className="btn small"
              onClick={() => api.checkout("plus").then((r) => window.location.assign(r.url)).catch((e: Error) => flash(e.message))}
            >
              Upgrade to Plus: unlimited letters
            </button>
          </div>
        )}
      </section>

      <section className="card stack">
        <h2>Counselling service</h2>
        <p className="muted">Counsellors join their service with an invite code from their admin.</p>
        <div className="row">
          <input aria-label="Invite code" placeholder="ABCD-EFGH-JKLM" value={code} onChange={(e) => setCode(e.target.value)} style={{ flex: 1, width: "auto" }} />
          <button
            className="btn small"
            disabled={code.length < 6}
            onClick={() => api.redeemInvite(code).then(() => window.location.assign("/counsellor/")).catch(() => flash("This code is not valid."))}
          >
            Join
          </button>
        </div>
      </section>

      <section className="card stack">
        <h2>Your data</h2>
        <p className="muted">
          Letters are deleted automatically after 30 days. You can download everything or delete your account now.
        </p>
        <div className="row">
          <button
            className="btn ghost small"
            onClick={() =>
              api.exportMe().then((data) => {
                const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
                const a = document.createElement("a");
                a.href = url;
                a.download = "letterlens-export.json";
                a.click();
                URL.revokeObjectURL(url);
