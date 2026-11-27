"use client";

import Link from "next/link";

import { EnvelopeArt } from "@/components/Brand";
import { Header } from "@/components/Shell";

const FEATURES = [
  {
    title: "Plain language, your language",
    text: "A short summary in English, Turkish, Arabic, Ukrainian, Russian or plain German. Point at a sentence to highlight the lines in the original that it comes from.",
  },
  {
    title: "Deadlines, checked",
    text: "Dates and amounts are checked against the letter. If a date cannot be found in the text, it is marked “please check”, never shown as a fact.",
  },
  {
    title: "A counsellor when you need one",
    text: "LetterLens explains; it does not give legal advice. If your counselling service uses LetterLens, you can share a letter with it. Only if you want, and you can stop at any time.",
  },
];

export default function Landing() {
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
            <div className="row">
              <Link className="btn" href="/signin/?mode=signup">
                Create a free account
              </Link>
              <Link className="btn ghost" href="/signin/">
                Sign in
              </Link>
            </div>
            <p className="faint" style={{ marginTop: 16 }}>
              General information, not legal advice. Photos and PDFs are read on your device; only the text is sent, to servers in the EU.
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
