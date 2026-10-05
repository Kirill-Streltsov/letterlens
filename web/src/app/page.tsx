"use client";

import { useEffect, useState } from "react";

import { EnvelopeArt } from "@/components/Brand";
import { Header } from "@/components/Shell";
import { setDevGroups, signIn } from "@/lib/auth";
import { type AppConfig, loadConfig } from "@/lib/config";

const FEATURES = [
  {
    title: "Plain language, your language",
    text: "A short summary in English, Turkish, Arabic, Ukrainian, Russian or plain German. Every sentence points to the line in the original.",
  },
  {
    title: "Deadlines you can trust",
    text: "Dates and amounts are checked against the letter. If a date cannot be found in the text, it is marked “please check”, never shown as a fact.",
  },
  {
    title: "A counsellor when you need one",
    text: "LetterLens explains; it does not give legal advice. Share a letter with a free counselling service with one tap, and only if you want.",
  },
];

export default function Landing() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [devUser, setDevUser] = useState("demo-client");

  useEffect(() => {
    loadConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  const local = config?.stage === "local";

  return (
    <>
      <Header />
      <main className="container">
        <section className="hero">
          <div>
            <p className="pill">For people who receive German official post</p>
            <h1>Understand the letter. Keep the deadline.</h1>
            <p className="lead">
              Tax office, Jobcenter, health insurer, immigration office, landlord: LetterLens tells you what the letter
              says, what it wants from you, and by when.
            </p>
            {local ? (
              <form
                className="card stack"
                style={{ maxWidth: 420 }}
                onSubmit={(e) => {
                  e.preventDefault();
                  if (devUser.startsWith("counsellor")) setDevGroups("counsellor");
                  void signIn(devUser);
                }}
              >
                <label htmlFor="dev-user">Local demo: sign in as</label>
                <input id="dev-user" value={devUser} onChange={(e) => setDevUser(e.target.value)} />
                <p className="faint">
                  Use <code>counsellor-anna</code> for the counsellor inbox (after <code>make seed</code>).
                </p>
                <button className="btn" type="submit">
                  Continue
                </button>
              </form>
            ) : (
              <div className="row">
                <button className="btn" onClick={() => void signIn()} disabled={!config}>
                  Sign in or create an account
                </button>
              </div>
            )}
            <p className="faint" style={{ marginTop: 16 }}>
              General information, not legal advice. Images stay on your device; only the text is processed, in the EU.
            </p>
          </div>
          <EnvelopeArt />
        </section>
        <section className="features">
          {FEATURES.map((f) => (
            <article className="card" key={f.title}>
              <h3>{f.title}</h3>
              <p className="muted">{f.text}</p>
            </article>
          ))}
        </section>
      </main>
    </>
  );
}
