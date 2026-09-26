"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AppPage } from "@/components/Shell";
import { api, type StatsRow } from "@/lib/api";
import { toCsv } from "@/lib/csv";
import { LETTER_TYPES } from "@/lib/format";

function Stats() {
  const tenant = useSearchParams().get("tenant") ?? "";
  const [rows, setRows] = useState<StatsRow[] | null>(null);
  const [invite, setInvite] = useState<string | null>(null);

  useEffect(() => {
    api.stats(tenant).then(setRows).catch(() => setRows([]));
  }, [tenant]);

  const total = rows?.reduce((s, r) => s + r.cases, 0) ?? 0;

