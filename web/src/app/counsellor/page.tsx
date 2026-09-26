"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { InboxArt } from "@/components/Brand";
import { AppPage } from "@/components/Shell";
import { api, type CaseItem, type Me } from "@/lib/api";
import { daysUntil, deadlinePill, formatDate, LETTER_TYPES, relativeLabel } from "@/lib/format";

const FILTERS = [
  { value: "", label: "All open" },
  { value: "new", label: "New" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
];

