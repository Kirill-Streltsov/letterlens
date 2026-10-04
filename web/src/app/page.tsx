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
