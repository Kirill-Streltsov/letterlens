"""Run real or sample letters (OCR text files) through the live pipeline and print a review.

Usage (from backend/, with LETTERLENS_LLM_PROVIDER and LETTERLENS_LLM_API_KEY set):
    PYTHONPATH=. uv run python scripts/review_letters.py [--lang uk] letter.txt [...]

Input: text with one OCR line per line and "=== page N" markers, for example the output of
tools/review/ocr.swift. Writes <file>.result.json next to each input. Do not commit letters
or results: they can contain personal data (docs/ai/evaluation.md, section 8).
"""

import argparse
import json
import sys
from pathlib import Path

from evals.run import make_context
from letterlens.domain import LetterDocument, OcrLine
from letterlens.pipeline import steps as S
from letterlens.pipeline.state import PipelineState

dropped: list[str] = []
_num, _adv = S.unsupported_numbers, S.is_advisory_output


def _num_hook(text, allowed):
    r = _num(text, allowed)
    if r:
        dropped.append(f"numbers {r}: {text}")
    return r


def _adv_hook(text):
    r = _adv(text)
    if r:
        dropped.append(f"advisory: {text}")
    return r


S.unsupported_numbers, S.is_advisory_output = _num_hook, _adv_hook


def document(path: Path) -> LetterDocument:
    lines, page, index = [], 1, 0
    for raw in path.read_text().splitlines():
        if raw.startswith("=== page"):
            page = int(raw.split()[-1])
            index = 0
            continue
        text = raw.strip()
        if not text or index >= 500:
            continue
        index += 1
        lines.append(OcrLine(page=page, index=index, text=text[:2000]))
    return LetterDocument(lines=lines, ocr_engine="apple-vision")


def review(path: Path, ctx, lang: str | None) -> None:
    dropped.clear()
    doc = document(path)
    state = PipelineState(letter_id=path.stem, owner_id="review", document=doc)
    for step in (S.classify, S.extract, S.verify_step, S.retrieve):
        state = step(state, ctx.deps)
    state = S.explain(state, ctx.deps, "en")
    if lang:
        state = S.explain(state, ctx.deps, lang)
    lm = doc.line_map()
    f, c = state.facts, state.classification
    out = [f"##### {path.stem}  ({len(doc.lines)} lines)"]
    out.append(f"type: {c.letter_type.value} p={c.confidence:.2f} abstained={c.abstained}")
    out.append(f"sender: {f.sender.value!r} | subject: {f.subject.value!r}")
    out.append(f"letter date: {f.letter_date} ({f.letter_date_status})")
    out.append(f"refs: {[(r.label, r.value) for r in f.reference_numbers]}")
    for d in f.deadlines:
        src = " / ".join(lm[i].text for i in d.line_ids if i in lm)[:140]
        out.append(
            f"DEADLINE {d.due_date} [{d.status}] est={d.is_estimate} {d.description!r} rule={d.rule!r} <- {src!r}"
        )
    for a in f.amounts:
        src = " / ".join(lm[i].text for i in a.line_ids if i in lm)[:120]
        out.append(f"AMOUNT {a.value} {a.currency} {a.direction} [{a.status}] {a.description!r} <- {src!r}")
    for act in getattr(f, "required_actions", []) or []:
        out.append(f"ACTION {act}")
    out.append(f"passages: {[p.doc_id for p in state.passages or []]}")
    exp = state.explanations["en"]
    out.append(f"HEADLINE {exp.headline}")
    for s in exp.summary:
        out.append(f"  - {s.text} {s.line_ids}")
    for st in exp.next_steps:
        out.append(f"  > {st.text} {st.citation_ids}")
    if lang and lang in state.explanations:
        t = state.explanations[lang]
        out.append(f"[{lang}] {len(t.summary)}/{len(exp.summary)} sentences: {t.headline}")
    out.append(f"degraded: {state.degraded} {state.degraded_reasons}")
    for d in dropped:
        out.append(f"DROPPED {d}")
    print("\n".join(out), flush=True)
    path.with_suffix(".result.json").write_text(
        json.dumps(
            {"facts": f.model_dump(mode="json"), "explanation": exp.model_dump(mode="json")},
            ensure_ascii=False,
            indent=1,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    ctx = make_context("live")
    for name in args.files:
        try:
            review(Path(name), ctx, args.lang)
        except Exception as exc:
            print(f"##### {name}: ERROR {type(exc).__name__}: {exc}", file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()
