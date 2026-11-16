# ADR-0006: The model proposes, code verifies

Status: accepted · Date: 2026-11-16

## Context

A wrong deadline can cost a reader money or a right. Models sometimes invent
dates, shift them, or cite the wrong line. A letter can also contain text that
tries to instruct the model.

## Decision

1. The extraction schema requires a line id for every value.
2. Deterministic code (`grounding/verifier.py`) parses the cited lines with German
   date and amount parsers. A value is `verified` only if the cited line contains it.
   Otherwise it is `needs_check` with a note for the reader.
3. Relative deadlines ("innerhalb eines Monats nach Bekanntgabe") are computed by code
   with the rules in `grounding/deadlines.py` (4-day notification fiction since
   1 January 2025, month arithmetic, weekend and holiday shift). They are always
   `needs_check`, with the rule shown.
4. Lines that look like instructions to a model are removed from the prompt and are never valid sources.
5. The explanation step is sanitized: sentences with numbers that are not in the letter or the facts are dropped; next steps without a valid citation are dropped.

## Consequences

- The safety property is measurable: "unsafe verified facts" must be 0. The release gate checks it, also with 91 injected hallucinations.
- Some correct values show as "please check" (precision over recall). The verified share is 94 % on the golden set.
- The deadline estimate covers only nationwide holidays. Regional holidays are a reason the state stays `needs_check`.
