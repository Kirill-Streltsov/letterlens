"""Evaluation suite and release gate.

Usage
  uv run python -m evals.run                       # offline profile (rules baseline), all suites
  uv run python -m evals.run --profile chaos       # fault injection: the model invents dates/amounts
  LETTERLENS_LLM_PROVIDER=mistral LETTERLENS_LLM_API_KEY=... \
  uv run python -m evals.run --profile live        # real model, adds the faithfulness suite
  uv run python -m evals.run --update-languages    # with --profile live: write language status

Exit code 1 when a gate in evals/thresholds.yaml fails. CI runs the offline and
chaos profiles on every pull request (.github/workflows/ci.yml).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from evals.handwritten import HANDWRITTEN
from letterlens.config import Settings
from letterlens.domain import FactStatus
from letterlens.llm import Gateway, InMemoryLedger, Task, build_provider
from letterlens.llm import prompts as P
from letterlens.llm.outputs import BackTranslation as _BackText
from letterlens.llm.outputs import GuardDecision
from letterlens.llm.providers.fake import FakeProvider
from letterlens.llm.types import LLMRequest, LLMResponse
from letterlens.ml.classifier import default_model
from letterlens.pipeline.state import InMemoryStateStore, PipelineState
from letterlens.pipeline.steps import STEP_FUNCTIONS, PipelineDeps, explain
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.guardrail import Verdict, check_question_rules
from letterlens.synthetic import SyntheticLetter, generate_corpus, to_document
from letterlens.synthetic.generator import AmountLabel, DeadlineLabel

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "golden" / "letters.jsonl"
REDTEAM = ROOT / "redteam" / "questions.jsonl"
THRESHOLDS = ROOT / "thresholds.yaml"
REPORTS = ROOT / "reports"
EXPLICIT_KINDS = {"explicit_date", "appointment"}

# Which corpus passages a good retrieval returns for each letter family.
EXPECTED_PASSAGES: dict[str, set[str]] = {
    "tax_assessment": {"tax-objection"},
    "tax_reminder": {"tax-return-reminder"},
    "tax_arrears": {"tax-late-payment"},
    "jobcenter_approval": {"benefits-objection"},
    "jobcenter_documents": {"cooperation-duty"},
    "jobcenter_invitation": {"jobcenter-appointment"},
    "familienkasse_refund": {"benefits-repayment", "tax-objection"},
    "insurance_arrears": {"health-arrears"},
    "insurance_questionnaire": {"family-insurance"},
    "insurance_rejection": {"benefits-objection"},
    "immigration_appointment": {"residence-renewal"},
    "immigration_hearing": {"hearing-letter"},
    "immigration_fiction": {"residence-renewal"},
    "landlord_utility_statement": {"utility-statement"},
    "landlord_rent_increase": {"rent-increase"},
    "landlord_reminder": {"rent-arrears"},
    "broadcast_fee": {"broadcast-fee"},
    "collection_agency": {"debt-collection"},
    "handwritten-court-order": {"court-payment-order"},
    "handwritten-termination": {"tenancy-termination"},
    "handwritten-jobcenter-change": {"benefits-repayment", "benefits-objection"},
    "handwritten-kindergeld-school": {"cooperation-duty"},
    "handwritten-sick-pay": {"benefits-objection"},
    "handwritten-injection": {"rent-arrears"},
}


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


def build_golden() -> list[SyntheticLetter]:
    """Deterministic golden set: unseen seeds of every template, OCR-noise variants, hand-written."""
    letters = generate_corpus(5, seed=2026)
    letters += generate_corpus(1, seed=4242, noise=0.2)
    return letters + HANDWRITTEN


def write_golden(letters: list[SyntheticLetter]) -> None:
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    with GOLDEN.open("w", encoding="utf-8") as f:
        for letter in letters:
            f.write(json.dumps(letter.to_dict(), ensure_ascii=False) + "\n")


def load_golden() -> list[SyntheticLetter]:
    if not GOLDEN.exists():
        write_golden(build_golden())
    out = []
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        raw["deadlines"] = [DeadlineLabel(**d) for d in raw["deadlines"]]
        raw["amounts"] = [AmountLabel(**a) for a in raw["amounts"]]
        out.append(SyntheticLetter(**raw))
    return out


# --------------------------------------------------------------------------
# Fault injection
# --------------------------------------------------------------------------


class ChaosProvider(FakeProvider):
    """Simulates a hallucinating model: shifts dates, changes amounts, cites wrong lines."""

    name = "chaos"

    def __init__(self, rate: float = 0.35, seed: int = 7) -> None:
        super().__init__()
        self.rate = rate
        self.rng = random.Random(seed)
        self.injected: list[tuple[str, str]] = []  # (kind, value)

    def complete(self, request: LLMRequest, timeout: float) -> LLMResponse:
        response = super().complete(request, timeout)
        if request.task is not Task.EXTRACT:
            return response
        data = json.loads(response.text)
        for d in data["deadlines"]:
            if d["date"] and self.rng.random() < self.rate:
                shifted = date.fromisoformat(d["date"]) + timedelta(days=self.rng.choice([1, 2, 7, -1]))
                d["date"] = shifted.isoformat()
                self.injected.append(("date", d["date"]))
        for a in data["amounts"]:
            if self.rng.random() < self.rate:
                a["value"] = str((Decimal(a["value"]) * Decimal("1.1")).quantize(Decimal("0.01")))
                self.injected.append(("amount", a["value"]))
        if data["letter_date"]["value"] and self.rng.random() < self.rate:
            data["letter_date"]["line_ids"] = ["p1-l1"]  # wrong citation
        text = json.dumps(data)
        return LLMResponse(
            text,
            response.model,
            self.name,
            response.input_tokens,
            response.output_tokens,
            response.latency_ms,
        )


# --------------------------------------------------------------------------
# Suites
# --------------------------------------------------------------------------


@dataclass
class Context:
    settings: Settings
    deps: PipelineDeps
    provider_name: str
    ledger: InMemoryLedger


def run_letter(ctx: Context, letter: SyntheticLetter, steps: tuple[str, ...]) -> PipelineState:
    store = InMemoryStateStore()
    state = PipelineState(letter_id=letter.id, owner_id="eval", document=to_document(letter))
    for step in steps:
        state = STEP_FUNCTIONS[step](state, ctx.deps)
    store.save_state(state)
    return state


def suite_classification(ctx: Context, letters: list[SyntheticLetter]) -> dict[str, Any]:
    model = default_model()
    per_class: dict[str, list[bool]] = defaultdict(list)
    subsets: dict[str, list[bool]] = defaultdict(list)
    confidences = []
    for letter in letters:
        result = model.classify("\n".join(letter.lines))
        ok = result.letter_type.value == letter.letter_type
        per_class[letter.letter_type].append(ok)
        subset = "handwritten" if letter.template_id.startswith("handwritten") else "synthetic"
        subsets[subset].append(ok)
        confidences.append((result.confidence, ok))
    bins: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for conf, ok in confidences:
        bins[min(int(conf * 10), 9)].append((conf, ok))
    ece = sum(
        len(b) / len(confidences) * abs(sum(o for _, o in b) / len(b) - sum(c for c, _ in b) / len(b))
        for b in bins.values()
    )
    recalls = {k: sum(v) / len(v) for k, v in per_class.items()}
    return {
        "synthetic_accuracy": sum(subsets["synthetic"]) / len(subsets["synthetic"]),
        "handwritten_accuracy": sum(subsets["handwritten"]) / max(len(subsets["handwritten"]), 1),
        "macro_recall": sum(recalls.values()) / len(recalls),
        "per_class_recall": recalls,
        "ece": round(ece, 4),
        "model_version": model.version,
    }


def suite_extraction(ctx: Context, letters: list[SyntheticLetter]) -> dict[str, Any]:
    c: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    grounding = []
    for letter in letters:
        state = run_letter(ctx, letter, ("classify", "extract", "verify"))
        facts = state.facts
        assert facts is not None
        grounding.append(facts.grounding_rate)
        expected_dates = {d.date for d in letter.deadlines if d.kind in EXPLICIT_KINDS}
        shown = {d.due_date.isoformat(): d for d in facts.deadlines if d.due_date and not d.is_estimate}
        verified = {k for k, d in shown.items() if d.status is FactStatus.VERIFIED}

