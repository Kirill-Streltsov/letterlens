"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EnvelopeArt } from "@/components/Brand";
import { AppPage } from "@/components/Shell";
import { api, type LetterListItem, type Me } from "@/lib/api";
import { daysUntil, deadlinePill, formatDate, LETTER_TYPES, relativeLabel } from "@/lib/format";

function Letters({ me }: { me: Me }) {
  const [letters, setLetters] = useState<LetterListItem[] | null>(null);

  useEffect(() => {
    api.letters().then(setLetters).catch(() => setLetters([]));
  }, []);

  const left = me.letters_limit === null ? null : Math.max(me.letters_limit - me.letters_this_month, 0);

