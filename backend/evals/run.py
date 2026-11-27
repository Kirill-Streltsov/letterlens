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

from evals.handwritten import HANDWRITTEN, KEY_POINTS
from letterlens.config import Settings
from letterlens.domain import FactStatus, Frozen
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
    "handwritten-study-warning": {"residence-for-study", "acknowledgement-of-receipt"},
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
        c["degraded_letters"] += state.degraded
        expected_dates = {d.date for d in letter.deadlines if d.kind in EXPLICIT_KINDS}
        shown = {d.due_date.isoformat(): d for d in facts.deadlines if d.due_date and not d.is_estimate}
        verified = {k for k, d in shown.items() if d.status is FactStatus.VERIFIED}

        c["letters"] += 1
        shown_date = facts.letter_date.isoformat() if facts.letter_date else None
        c["letter_date_ok"] += shown_date == (letter.letter_date or None)  # "" = no date in the letter
        c["expected_dates"] += len(expected_dates)
        c["found_dates"] += len(expected_dates & set(shown))
        c["shown_dates"] += len(shown)
        c["correct_shown_dates"] += len(set(shown) & expected_dates)
        c["verified_dates"] += len(verified)
        c["unsafe_verified_dates"] += len(verified - expected_dates)
        c["exact_letters"] += set(shown) == expected_dates

        expected_rel = sum(1 for d in letter.deadlines if d.kind == "relative")
        found_rel = sum(1 for d in facts.deadlines if d.is_estimate)
        c["expected_relative"] += expected_rel
        c["found_relative"] += min(expected_rel, found_rel)

        expected_amounts = {Decimal(a.value): a.direction for a in letter.amounts}
        shown_amounts = {a.value: a for a in facts.amounts}
        c["expected_amounts"] += len(expected_amounts)
        c["found_amounts"] += len(set(expected_amounts) & set(shown_amounts))
        c["shown_amounts"] += len(shown_amounts)
        c["verified_amounts"] += sum(a.status is FactStatus.VERIFIED for a in shown_amounts.values())
        c["unsafe_verified_amounts"] += sum(
            a.status is FactStatus.VERIFIED and v not in expected_amounts for v, a in shown_amounts.items()
        )
        for value, direction in expected_amounts.items():
            if value in shown_amounts:
                c["direction_checked"] += 1
                c["direction_ok"] += shown_amounts[value].direction == direction
        if set(shown) != expected_dates or set(expected_amounts) - set(shown_amounts):
            failures.append(
                {
                    "id": letter.id,
                    "expected_dates": sorted(expected_dates),
                    "shown_dates": sorted(shown),
                    "missing_amounts": sorted(str(v) for v in set(expected_amounts) - set(shown_amounts)),
                }
            )

    def ratio(a: str, b: str) -> float:
        return round(c[a] / c[b], 4) if c[b] else 1.0

    result = {
        "letters": c["letters"],
        "letter_date_accuracy": ratio("letter_date_ok", "letters"),
        "explicit_deadline_recall": ratio("found_dates", "expected_dates"),
        "explicit_deadline_precision": ratio("correct_shown_dates", "shown_dates"),
        "deadline_exact_match_letters": ratio("exact_letters", "letters"),
        "relative_deadline_recall": ratio("found_relative", "expected_relative"),
        "amount_recall": ratio("found_amounts", "expected_amounts"),
        "amount_direction_accuracy": ratio("direction_ok", "direction_checked"),
        "unsafe_verified_dates": c["unsafe_verified_dates"],
        "unsafe_verified_amounts": c["unsafe_verified_amounts"],
        "verified_share_of_dates": ratio("verified_dates", "shown_dates"),
        "mean_grounding_rate": round(sum(grounding) / len(grounding), 4),
        # Letters where the model failed and the rules took over. In the live profile this
        # must be 0, otherwise the "live" numbers would silently be the rules baseline.
        "degraded_letters": c["degraded_letters"],
        "failures": failures[:25],
    }
    provider = ctx.deps.gateway.provider
    if isinstance(provider, ChaosProvider):
        result["injected_errors"] = len(provider.injected)
    return result


def suite_retrieval(ctx: Context, letters: list[SyntheticLetter]) -> dict[str, Any]:
    hits, rr, n = 0, 0.0, 0
    misses = []
    for letter in letters:
        expected = EXPECTED_PASSAGES.get(letter.template_id)
        if not expected:
            continue
        state = run_letter(ctx, letter, ("classify", "extract", "verify", "retrieve"))
        ids = [p.doc_id for p in state.passages or []]
        n += 1
        rank = next((i for i, d in enumerate(ids, 1) if d in expected), None)
        hits += rank is not None
        rr += 1 / rank if rank else 0.0
        if rank is None:
            misses.append({"id": letter.id, "got": ids, "expected": sorted(expected)})
    return {"letters": n, "recall_at_4": round(hits / n, 4), "mrr": round(rr / n, 4), "misses": misses[:20]}


def suite_guardrail(ctx: Context) -> dict[str, Any]:
    rows = [json.loads(x) for x in REDTEAM.read_text(encoding="utf-8").splitlines()]
    by_lang: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    for row in rows:
        rules = check_question_rules(row["text"])
        decision = ctx.deps.gateway.generate(  # a provider error fails the run on purpose
            Task.GUARD,
            GuardDecision,
            P.GUARD_SYSTEM,
            P.guard_user(row["text"]),
            P.GUARD_VERSION,
            context={"question": row["text"]},
            max_tokens=300,
        )
        llm_block = decision.category in {"individual_legal_advice", "prompt_injection"}
        combined = rules.blocked or llm_block
        label, lang = row["label"], row["lang"]
        totals[f"{label}_n"] += 1
        totals[f"{label}_rules"] += rules.blocked
        totals[f"{label}_combined"] += combined
        by_lang[lang][f"{label}_n"] += 1
        by_lang[lang][f"{label}_combined"] += combined
        if label == "injection":
            totals["injection_typed"] += (
                rules.verdict is Verdict.INJECTION or decision.category == "prompt_injection"
            )

    def rate(k: str, n: str, src: Counter[str] = totals) -> float:
        return round(src[k] / src[n], 4) if src[n] else 0.0

    return {
        "questions": len(rows),
        "advice_catch_rate": rate("advice_combined", "advice_n"),
        "advice_catch_rate_rules_only": rate("advice_rules", "advice_n"),
        "benign_false_positive_rate": rate("benign_combined", "benign_n"),
        "injection_catch_rate": rate("injection_combined", "injection_n"),
        "per_language_advice_catch": {
            lang: rate("advice_combined", "advice_n", c)
            for lang, c in sorted(by_lang.items())
            if c["advice_n"]
        },
        "per_language_false_positive": {
            lang: rate("benign_combined", "benign_n", c)
            for lang, c in sorted(by_lang.items())
            if c["benign_n"]
        },
    }


JUDGE_SYSTEM = """You compare two summaries of the same letter. A is the reference (English).
B is a back-translation into English of a summary in another language.
Score how faithful B is to A from 1 (contradicts or invents facts) to 5 (same facts).
Any changed date, amount, deadline, sender or required action is a major error (score 1 or 2).
Return JSON only."""


def suite_faithfulness(ctx: Context, letters: list[SyntheticLetter], sample: int) -> dict[str, Any]:
    """Live only. Back-translation + LLM judge, per language. The judge is validated first."""
    from evals.judge import JudgeScore, validate_judge

    gw = ctx.deps.gateway
    judge_accuracy = validate_judge(gw, JUDGE_SYSTEM)
    rng = random.Random(1)
    picked = rng.sample([x for x in letters if not x.template_id.startswith("handwritten")], sample)
    from letterlens.i18n import languages

    scores: dict[str, list[float]] = defaultdict(list)
    low: list[dict[str, Any]] = []  # judge reasons for scores below 4, to see what goes wrong
    for letter in picked:
        state = run_letter(ctx, letter, ("classify", "extract", "verify", "retrieve"))
        state = explain(state, ctx.deps, "en")
        reference = " ".join(s.text for s in state.explanations["en"].summary)
        for code in languages():
            if code == "en":
                continue
            state = explain(state, ctx.deps, code)
            target = " ".join(s.text for s in state.explanations[code].summary)
            back = gw.generate(
                Task.BACKTRANSLATE,
                _BackText,
                P.BACKTRANSLATE_SYSTEM,
                target,
                P.BACKTRANSLATE_VERSION,
                context={"text": target},
                max_tokens=1500,
            )
            score = gw.generate(
                Task.GUARD,
                JudgeScore,
                JUDGE_SYSTEM,
                f"A: {reference}\n\nB: {back.text}",
                "judge-v1",
                max_tokens=400,
            )
            scores[code].append(score.score / 5)
            if score.score < 4:
                low.append(
                    {"letter": letter.id, "language": code, "score": score.score, "issues": score.issues}
                )
    return {
        "judge_accuracy_on_calibration_set": judge_accuracy,
        "letters": len(picked),
        "per_language": {k: round(sum(v) / len(v), 4) for k, v in scores.items()},
        "min_language_score": round(min((sum(v) / len(v) for v in scores.values()), default=0.0), 4),
        "low_scores": low,
    }


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------


class KeyPointVerdict(Frozen):
    index: int
    present: bool


class KeyPointJudgement(Frozen):
    points: list[KeyPointVerdict]


KEYPOINT_JUDGE = """You check whether a summary of a letter contains given key points.
For each numbered key point, answer present = true only if the summary states the same fact
(the wording may differ; numbers, dates and amounts must match). Return JSON only."""


def judge_keypoints(gw: Gateway, summary: str, points: list[str]) -> list[bool]:
    listing = "\n".join(f"{i}. {p}" for i, p in enumerate(points, 1))
    result = gw.generate(
        Task.GUARD,
        KeyPointJudgement,
        KEYPOINT_JUDGE,
        f"<summary>\n{summary}\n</summary>\n\n<key_points>\n{listing}\n</key_points>",
        "keypoints-v1",
        max_tokens=600,
    )
    found = {v.index: v.present for v in result.points}
    return [bool(found.get(i, False)) for i in range(1, len(points) + 1)]


def suite_completeness(ctx: Context, letters: list[SyntheticLetter]) -> dict[str, Any]:
    """Live only. Does the explanation contain the points that matter most?"""
    gw = ctx.deps.gateway
    by_id = {x.id: x for x in letters}
    total = hits = probe_hits = probe_total = 0
    per_letter: dict[str, float] = {}
    missed: list[str] = []
    for letter_id, points in KEY_POINTS.items():
        letter = by_id.get(letter_id)
        if letter is None:
            continue
        state = run_letter(ctx, letter, ("classify", "extract", "verify", "retrieve"))
        state = explain(state, ctx.deps, "en")
        exp = state.explanations["en"]
        text = " ".join([exp.headline] + [s.text for s in exp.summary])
        verdicts = judge_keypoints(gw, text, points)
        hits += sum(verdicts)
        total += len(points)
        per_letter[letter_id] = round(sum(verdicts) / len(points), 3)
        missed += [f"{letter_id}: {p}" for p, ok in zip(points, verdicts, strict=True) if not ok]
        # Calibration probe: an empty summary must not "contain" the points.
        probe = judge_keypoints(gw, "This is an official letter.", points)
        probe_hits += sum(probe)
        probe_total += len(points)
    return {
        "letters": len(per_letter),
        "keypoint_recall": round(hits / total, 4) if total else 0.0,
        "judge_false_positive_rate": round(probe_hits / probe_total, 4) if probe_total else 0.0,
        "per_letter": per_letter,
        "missed": missed,
    }


def lookup(report: dict[str, Any], dotted: str) -> Any:
    node: Any = report
    for part in dotted.split("."):
        node = node[part]
    return node


def check_gates(report: dict[str, Any], profile: str) -> list[str]:
    config = yaml.safe_load(THRESHOLDS.read_text(encoding="utf-8"))
    failures = []
    for gate in config.get(profile, []):
        try:
            value = lookup(report, gate["metric"])
        except KeyError:
            continue  # suite not run in this invocation
        if "min" in gate and value < gate["min"]:
            failures.append(f"{gate['metric']} = {value} < {gate['min']}")
        if "max" in gate and value > gate["max"]:
            failures.append(f"{gate['metric']} = {value} > {gate['max']}")
    return failures


def make_context(profile: str) -> Context:
    if profile == "live":
        settings = Settings()
        provider = build_provider(settings)
        if provider.name == "fake":
            sys.exit("profile 'live' needs LETTERLENS_LLM_PROVIDER and LETTERLENS_LLM_API_KEY")
    else:
        settings = Settings(env="test", llm_provider="fake")
        provider = ChaosProvider() if profile == "chaos" else FakeProvider()
    ledger = InMemoryLedger()
    gateway = Gateway(provider, settings, ledger, sleep=time.sleep)
    deps = PipelineDeps(gateway, HybridRetriever(), default_model())
    return Context(settings, deps, provider.name, ledger)


def summary_markdown(report: dict[str, Any], failures: list[str]) -> str:
    lines = [
        f"# Evaluation report: profile `{report['profile']}`",
        "",
        f"Provider: `{report['provider']}`. Prompts: `{report['prompt_versions']}`.",
        "",
    ]
    for suite, metrics in report["suites"].items():
        lines += [f"## {suite}", "", "| Metric | Value |", "|---|---|"]
        for key, value in metrics.items():
            if isinstance(value, (int, float, str)):
                lines.append(f"| {key} | {value} |")
        lines.append("")
    lines += ["## Gate", ""] + ([f"- FAIL: {f}" for f in failures] or ["- PASS: all gates"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", choices=["offline", "chaos", "live"], default="offline")
    parser.add_argument(
        "--suite",
        action="append",
        choices=["classification", "extraction", "retrieval", "guardrail", "faithfulness", "completeness"],
    )
    parser.add_argument("--sample", type=int, default=8, help="letters for the faithfulness suite")
    parser.add_argument("--rebuild-golden", action="store_true")
    parser.add_argument("--update-languages", action="store_true")
    args = parser.parse_args(argv)

    if args.rebuild_golden:
        write_golden(build_golden())
    letters = load_golden()
    ctx = make_context(args.profile)
    suites = args.suite or (
        ["extraction"]
        if args.profile == "chaos"
        else ["classification", "extraction", "retrieval", "guardrail"]
        + (["faithfulness", "completeness"] if args.profile == "live" else [])
    )
    started = time.time()
    report: dict[str, Any] = {
        "profile": args.profile,
        "provider": ctx.provider_name,
        "prompt_versions": [P.EXTRACT_VERSION, P.EXPLAIN_VERSION, P.GUARD_VERSION],
        "golden_letters": len(letters),
        "suites": {},
    }
    for suite in suites:
        if suite == "classification":
            report["suites"][suite] = suite_classification(ctx, letters)
        elif suite == "extraction":
            report["suites"][suite] = suite_extraction(ctx, letters)
        elif suite == "retrieval":
            report["suites"][suite] = suite_retrieval(ctx, letters)
        elif suite == "guardrail":
            report["suites"][suite] = suite_guardrail(ctx)
        elif suite == "faithfulness":
            report["suites"][suite] = suite_faithfulness(ctx, letters, args.sample)
        elif suite == "completeness":
            report["suites"][suite] = suite_completeness(ctx, letters)
    report["seconds"] = round(time.time() - started, 1)
    report["llm_calls"] = len(ctx.ledger.calls)
    report["llm_list_price_usd"] = round(sum(c.list_price_usd for c in ctx.ledger.calls), 4)

    failures = check_gates({k: v for k, v in report.items()} | {"suites": report["suites"]}, args.profile)
    report["gate"] = {"passed": not failures, "failures": failures}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{args.profile}.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (REPORTS / f"{args.profile}.md").write_text(summary_markdown(report, failures), encoding="utf-8")

    if args.update_languages and args.profile == "live" and "faithfulness" in report["suites"]:
        from evals.judge import update_languages

        update_languages(report["suites"]["faithfulness"])

    print(summary_markdown(report, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
