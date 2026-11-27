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
      { id: "d1", due_date: "2027-02-12", status: "verified", is_estimate: false, description: "Pay", source_text: null, line_ids: ["p1-l2"], rule: null, note: null },
      { id: "d2", due_date: "2027-03-01", status: "needs_check", is_estimate: true, description: "Objection", source_text: null, line_ids: [], rule: "1 months", note: "Estimated" },
    ],
    amounts: [],
    required_actions: [],
    grounding_rate: 1,
  },
  explanation: null,
  explanation_languages: [],
  degraded: true,
  degraded_reasons: ["extract:BudgetExceededError"],
  image_urls: [],
  shares: [],
} as unknown as LetterView;

const explanation = {
  language: "ar",
  headline: "رسالة من مكتب الضرائب",
  letter_kind: "tax",
  summary: [{ text: "يجب الدفع.", line_ids: ["p1-l2"] }],
  next_steps: [],
  deadline_labels: { d1: "الدفع" },
  amount_labels: {},
  citations: [],
  counselling_hint: "hint",
  disclaimer: "General information, not legal advice.",
  faithfulness: null,
  model: "m",
};

describe("LetterWorkspace", () => {
  it("marks verified and unverified deadlines differently", () => {
    render(<LetterWorkspace letter={letter} explanation={null} />);
    expect(screen.getByText("Found in the letter")).toBeInTheDocument();
    expect(screen.getByText("Please check")).toBeInTheDocument();
    expect(screen.getByText(/simple rules/)).toBeInTheDocument();
  });

  it("highlights the source line of a summary sentence and renders RTL", () => {
    Element.prototype.scrollIntoView = () => undefined;
    const { container } = render(<LetterWorkspace letter={letter} explanation={explanation as never} />);
    fireEvent.mouseEnter(screen.getByText("يجب الدفع."));
    expect(container.querySelector("#p1-l2")).toHaveClass("hl");
    expect(container.querySelector("[dir='rtl']")).not.toBeNull();
    expect(screen.getByText("الدفع")).toBeInTheDocument();
  });
});

describe("citations", () => {
  it("numbers inline citations by their position in the source list", () => {
    const withSources = {
      ...explanation,
      language: "ru",
      next_steps: [
        { text: "Шаг один.", citation_ids: ["c2"] },
        { text: "Шаг два.", citation_ids: ["c4"] },
      ],
      citations: [
        { id: "c2", title: "Free migration counselling", source_url: "https://www.bamf.de", source_name: "BAMF", checked_on: "2026-11-26" },
        { id: "c4", title: "General steps", source_url: "https://www.gesetze-im-internet.de", source_name: "BGB", checked_on: "2026-11-26" },
      ],
    };
    render(<LetterWorkspace letter={letter} explanation={withSources as never} />);
    expect(screen.getByText("[1]")).toBeInTheDocument();
    expect(screen.getByText("[2]")).toBeInTheDocument();
    expect(screen.queryByText("[4]")).not.toBeInTheDocument();
  });
});
