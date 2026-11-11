# LetterLens

Scan an official German letter. Understand it in your language. Never miss the deadline.

LetterLens reads letters from the tax office, the Jobcenter, health insurers, the
immigration office and landlords. It explains each letter in plain language,
finds the deadlines and amounts, and checks every date against the original text.
It gives general information, not legal advice. For an individual case, it hands
the letter over to a free counselling service, with the reader's consent.

| Client | For | Main functions |
|---|---|---|
| iOS app (SwiftUI) | People who receive letters | Document scanner, on-device text recognition, summary in 6 languages, deadline cards with calendar and reminders, questions, sharing with a counsellor |
| Web app (Next.js) | Readers and counselling services | The same reader flow with in-browser text recognition; a case inbox, German summaries, reply translation and statistics for funding reports |

## Results

Measured on the golden set of 126 letters (synthetic letters with unseen seeds,
OCR-noise variants and 12 hand-written letters) and on 96 red-team questions in
6 languages. Report: [backend/evals/reports/offline.md](backend/evals/reports/offline.md).

| Metric | Value |
|---|---|
| Dates or amounts shown as "verified" that are not in the letter | **0** (also 0 of 91 injected hallucinations, fault-injection run) |
| Explicit deadline recall / precision | 98.0 % / 94.1 % |
| Letter date accuracy, amount recall | 100 % / 100 % |
| Letter-type accuracy on unseen layouts (leave-one-template-out) | 97.8 %, calibration error 0.32 → 0.01 |
| Retrieval recall@4 | 99.1 % |
| Legal-advice requests caught (rules layer only) / false positives | 85.2 % / 0 % |
| Prompt-injection attempts caught | 100 % |

