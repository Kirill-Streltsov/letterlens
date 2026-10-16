import { fireEvent, render, screen } from "@testing-library/react";

import { LetterWorkspace } from "@/components/LetterWorkspace";
import type { LetterView } from "@/lib/api";

const letter = {
  id: "l1",
  status: "ready",
  error: null,
  language: "en",
  created_at: "2026-11-01T10:00:00Z",
  expires_at: "2026-12-01T10:00:00Z",
  lines: [
    { page: 1, index: 1, text: "Finanzamt Bochum", bbox: null, confidence: null },
    { page: 1, index: 2, text: "Bitte zahlen Sie bis zum 12.02.2027.", bbox: null, confidence: null },
  ],
  classification: { letter_type: "tax", confidence: 0.99, probabilities: {}, model_version: "t", abstained: false },
  facts: {
    sender: { value: "Finanzamt Bochum", line_ids: ["p1-l1"] },
    subject: { value: null, line_ids: [] },
    letter_date: null,
    letter_date_status: "needs_check",
    reference_numbers: [],
    deadlines: [
